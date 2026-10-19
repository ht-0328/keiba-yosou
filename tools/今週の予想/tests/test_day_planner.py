"""買うレースの計画（財布・レースの選び方・金額・買い目の記録）。回顧の DuckDB は一時フォルダ、元DB は使わない（複勝の票数は無い）。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from yosou.review import ReviewStore, names

from 今週の予想 import forecast_columns as columns
from 今週の予想.bet_recorder import BetRecorder
from 今週の予想.day_planner import DayPlanner
from 今週の予想.race_plan import NO_BET
from 今週の予想.wallet import COMBO_WALLET, MATCH_WALLET, POLICY_WALLET, WIN_WALLET, Wallet


def _forecast(rid: str, klass: str, values: list[float], field_size: int = 16, odds_known: bool = True) -> dict:
    horses = [{columns.HORSE_NO: no, columns.PROBABILITY: 0.3, columns.PLACE_VALUE: value, columns.MARK: "－"} for no, value in enumerate(values, start=1)]
    tickets = [{"rule": "複勝", "horses": [no], "odds": 3.0, "dropped": ""} for no, value in enumerate(values, start=1) if value >= 1.25][:3]
    return {"rid": rid, "title": rid, "timing": "当日", "odds_known": odds_known, "made_at": "2026-10-11T10:00:00",
            "header": {"クラス": klass, "頭数": field_size}, "horses": horses, "tickets": tickets}


@pytest.fixture
def store(tmp_path: Path) -> ReviewStore:
    return ReviewStore(tmp_path / "review.duckdb")


@pytest.fixture
def con():
    """複勝の票数を読む表（``o1``）が空の元DB の代わり（票数の上限は無し）。"""
    from 共通 import keys
    with duckdb.connect(":memory:") as con:
        columns = ", ".join(f'{keys.q(name)} VARCHAR' for name in (*keys.RACE_KEY, "データ区分", "発表月日時分", "複勝票数合計"))
        con.execute(f"CREATE TABLE o1 ({columns})")
        yield con


def test_財布は_初めの額と買い目の記録から残高を数え_予算を割合で決める(store: ReviewStore, tmp_path: Path):
    wallet = Wallet(store, tmp_path / "財布.json")
    assert wallet.initial() == {MATCH_WALLET: 100_000, POLICY_WALLET: 30_000, WIN_WALLET: 100_000, COMBO_WALLET: 500_000}
    day = date(2026, 10, 11)
    assert wallet.budget(names.MATCH, day) == 5_000 and wallet.unit(day) == 1_600 and wallet.day_cap(day) == 20_000
    assert wallet.budget(names.POLICY_STAKES, day) == 900 and wallet.budget(names.POLICY_DAY, day) == 400
    # 9月に 10,000円 買って 4,000円 戻った → 10月の残高は 94,000円。月初の残高で決めるので、10月の買い目は10月の予算に入らない
    import pandas as pd
    store.write(names.BETS_TABLE, pd.DataFrame([
        {names.RACE_ID: "r1", names.TICKET_TYPE: "複勝", names.COMBO: "01", names.RACE_DATE: date(2026, 9, 20), names.PARTICIPATION: names.MATCH,
         names.RECORD_ONLY: False, names.STAKE_YEN: 10_000, names.PAYOUT_YEN: 4_000, names.SETTLED: True},
        {names.RACE_ID: "r2", names.TICKET_TYPE: "複勝", names.COMBO: "01", names.RACE_DATE: date(2026, 10, 4), names.PARTICIPATION: names.MATCH,
         names.RECORD_ONLY: False, names.STAKE_YEN: 5_000, names.PAYOUT_YEN: None, names.SETTLED: False},
    ]))
    assert wallet.balance(MATCH_WALLET) == 89_000 and wallet.balance(MATCH_WALLET, date(2026, 10, 1)) == 94_000
    assert wallet.budget(names.MATCH, day) == 4_700 and not wallet.stopped(day)


def test_計画は_重賞を必ず入れ_Eの大きい順に3つまで勝負にし_堅い重賞はノルマで買う(store: ReviewStore, tmp_path: Path, con):
    planner = DayPlanner(Wallet(store, tmp_path / "財布.json"))
    forecasts = [
        _forecast("2026101105040401", "G3", [1.0, 1.0, 1.1]),                 # 堅い重賞 → ノルマ（重賞）。線に届かなくても上から2点
        _forecast("2026101105040402", "1勝クラス", [1.6, 1.3, 1.0]),          # E = 0.9
        _forecast("2026101105040403", "2勝クラス", [1.3, 1.0, 1.0]),          # E = 0.3
        _forecast("2026101105040404", "3勝クラス", [1.4, 1.0, 1.0]),          # E = 0.4
        _forecast("2026101105040405", "オープン", [1.26, 1.0, 1.0]),          # E = 0.26 → 4位で外れる
        _forecast("2026101105040406", "新馬", [1.9, 1.0, 1.0]),               # 新馬は勝負にしない
        _forecast("2026101105040407", "1勝クラス", [1.9, 1.0, 1.0], field_size=7),   # 7頭以下
        _forecast("2026101105040408", "1勝クラス", [1.1, 1.0, 1.0]),          # E = 0
    ]
    plans = {plan.rid[-2:]: plan for plan in planner.plan(con, date(2026, 10, 11), forecasts)}
    assert plans["01"].kind == names.POLICY_STAKES and [pick.horse_no for pick in plans["01"].picks] == [3, 1] and plans["01"].stake_yen == 800
    assert [plans[no].kind for no in ("02", "03", "04")] == [names.MATCH] * 3 and plans["05"].kind == NO_BET and "上位3つ" in plans["05"].reason
    assert plans["06"].kind == NO_BET and plans["07"].kind == NO_BET and plans["08"].kind == NO_BET
    # 勝負レース: 線以上の馬だけ、1.40 以上は 2単位（ケリー基準の4分の1の中）。02 は 1.6（2単位 → 3,200 だがケリーで 1,600 以上に収まる）と 1.3（1単位）
    picks = plans["02"].picks
    assert [pick.horse_no for pick in picks] == [1, 2] and picks[1].yen == 1_600 and 1_600 <= picks[0].yen <= 3_200
    assert plans["02"].stake_yen <= plans["02"].budget_yen == 5_000


def test_勝負も重賞も無い日は_最大の期待値のレースをノルマ日の予備にする(store: ReviewStore, tmp_path: Path, con):
    planner = DayPlanner(Wallet(store, tmp_path / "財布.json"))
    forecasts = [_forecast("2026101105040401", "1勝クラス", [1.2, 1.0]), _forecast("2026101105040402", "2勝クラス", [1.1, 1.0]),
                 _forecast("2026101105040403", "木曜", [1.3, 1.0], odds_known=False)]
    plans = {plan.rid[-2:]: plan for plan in planner.plan(con, date(2026, 10, 11), forecasts)}
    assert set(plans) == {"01", "02"}   # オッズの無い木曜の予想は計画しない
    assert plans["01"].kind == names.POLICY_DAY and len(plans["01"].picks) == 1 and plans["01"].picks[0].yen == 400 and plans["02"].kind == NO_BET


def test_買い目の記録は_計画の複勝を書き_同じレースの未精算の行は書き直す(store: ReviewStore, tmp_path: Path, con):
    planner, recorder = DayPlanner(Wallet(store, tmp_path / "財布.json")), BetRecorder(store)
    plans = planner.plan(con, date(2026, 10, 11), [_forecast("2026101105040402", "1勝クラス", [1.6, 1.3, 1.0])])
    assert recorder.record(plans, "2026-10-11T10:00:00") == 2
    again = planner.plan(con, date(2026, 10, 11), [_forecast("2026101105040402", "1勝クラス", [1.6, 1.0, 1.0])])
    assert recorder.record(again, "2026-10-11T11:00:00") == 1
    bets = store.read(names.BETS_TABLE)
    assert len(bets) == 1 and bets.iloc[0][names.COMBO] == "01" and bets.iloc[0][names.PARTICIPATION] == names.MATCH and not bets.iloc[0][names.SETTLED]


def _high_forecast(rid: str, timing: str = "当日", expectation: str = "高") -> dict:
    """期待度つきのレース。◎ は 3番（単勝の期待値 1.12）。複勝の買い目は無い。単勝（期待値）1点（3番）と、◎ の単勝・馬単 3点（1点はトリガミで外した）。"""
    forecast = _forecast(rid, "1勝クラス", [1.0, 1.0, 1.0, 1.0])
    forecast["horses"][2].update({columns.MARK: "◎", columns.WIN_VALUE: 1.12})
    forecast.update(timing=timing, expectation=expectation, tickets=[
        {"rule": "単勝", "ticket_type": "単勝", "combo": "03", "label": "3", "odds": 4.0, "dropped": ""},
        {"rule": "単勝（期待値）", "ticket_type": "単勝", "combo": "03", "label": "3", "odds": 4.0, "value": 1.12, "dropped": ""},
        {"rule": "馬単", "ticket_type": "馬単", "combo": "0301", "label": "3→1", "odds": 30.0, "dropped": ""},
        {"rule": "馬単", "ticket_type": "馬単", "combo": "0302", "label": "3→2", "odds": 60.0, "dropped": ""},
        {"rule": "馬単", "ticket_type": "馬単", "combo": "0304", "label": "3→4", "odds": 1.5, "dropped": "トリガミ"},
        {"rule": "馬連", "ticket_type": "馬連", "combo": "0103", "label": "1-3", "odds": 12.0, "dropped": ""},
    ])
    return forecast


def test_単勝と馬単の1点は単勝馬単用の財布の割合で100円に届かなければ買わず_古い財布のファイルには書き足す(store: ReviewStore, tmp_path: Path):
    import json
    path = tmp_path / "財布.json"
    path.write_text(json.dumps({MATCH_WALLET: 100_000, POLICY_WALLET: 30_000}), encoding="utf-8")   # 単勝・馬単用を足す前のファイル
    wallet = Wallet(store, path)
    assert wallet.initial()[WIN_WALLET] == 100_000 and WIN_WALLET in json.loads(path.read_text(encoding="utf-8"))
    day = date(2026, 10, 11)
    assert wallet.point_yen("単勝", day) == 300 and wallet.point_yen("馬単", day) == 0   # 単勝は 370円の切り捨て、馬単は 12円で 100円に届かない
    path.write_text(json.dumps({MATCH_WALLET: 100_000, POLICY_WALLET: 30_000, WIN_WALLET: 1_000_000}), encoding="utf-8")
    assert wallet.point_yen("単勝", day) == 3_700 and wallet.point_yen("馬単", day) == 100


def test_当日の予想は複勝と別に単勝期待値を買い_期待度高なら馬単も買い_前日は買わない(store: ReviewStore, tmp_path: Path, con):
    import json
    path = tmp_path / "財布.json"
    path.write_text(json.dumps({MATCH_WALLET: 100_000, POLICY_WALLET: 30_000, WIN_WALLET: 1_000_000}), encoding="utf-8")
    planner = DayPlanner(Wallet(store, path))
    forecasts = [_high_forecast("2026101105040401"), _high_forecast("2026101105040402", timing="前日"),
                 _high_forecast("2026101105040403", expectation="低"), _forecast("2026101105040409", "1勝クラス", [1.6, 1.0])]   # 09 は複勝の勝負
    plans = {plan.rid[-2:]: plan for plan in planner.plan(con, date(2026, 10, 11), forecasts)}
    bought = plans["01"]
    assert bought.kind == NO_BET and bought.buys   # 複勝は買わないが、単勝と馬単は買う
    assert [(ticket.ticket_type, ticket.combo, ticket.yen) for ticket in bought.tickets] == [("単勝", "03", 3_700), ("馬単", "0301", 100), ("馬単", "0302", 100)]
    assert bought.tickets[0].value == pytest.approx(1.12) and bought.tickets[1].value is None
    assert bought.ticket_yen == 3_900 and bought.stake_yen == 3_900 and "期待度「高」" in bought.ticket_reason
    assert plans["02"].tickets == () and "前日" in plans["02"].ticket_reason
    # 期待度「低」でも単勝（期待値）は買う（◎ の馬単は買わない）
    assert [(ticket.ticket_type, ticket.combo) for ticket in plans["03"].tickets] == [("単勝", "03")] and "馬単" not in plans["03"].ticket_reason


def test_財布が小さいうちは馬単を買わず_単勝馬単用が止まりの線を割れば単勝も止める(store: ReviewStore, tmp_path: Path, con):
    import pandas as pd
    planner = DayPlanner(Wallet(store, tmp_path / "財布.json"))
    plan = planner.plan(con, date(2026, 10, 11), [_high_forecast("2026101105040401")])[0]
    assert [ticket.ticket_type for ticket in plan.tickets] == ["単勝"] and "馬単は1点が 100円に届かない" in plan.ticket_reason
    store.write(names.BETS_TABLE, pd.DataFrame([
        {names.RACE_ID: "r1", names.TICKET_TYPE: "単勝", names.COMBO: "01", names.RACE_DATE: date(2026, 9, 20), names.PARTICIPATION: names.MATCH_WIN,
         names.RECORD_ONLY: False, names.STAKE_YEN: 40_000, names.PAYOUT_YEN: 0, names.SETTLED: True},
    ]))
    stopped = planner.plan(con, date(2026, 10, 11), [_high_forecast("2026101105040401")])[0]
    assert stopped.tickets == () and "70%" in stopped.ticket_reason


def test_買い目の記録は_単勝と馬単を勝負単勝馬単として書く(store: ReviewStore, tmp_path: Path, con):
    import json
    path = tmp_path / "財布.json"
    path.write_text(json.dumps({MATCH_WALLET: 100_000, POLICY_WALLET: 30_000, WIN_WALLET: 1_000_000}), encoding="utf-8")
    forecasts = [_high_forecast("2026101105040401"), _forecast("2026101105040409", "1勝クラス", [1.6, 1.0])]   # 09 は複勝の勝負
    plans = DayPlanner(Wallet(store, path)).plan(con, date(2026, 10, 11), forecasts)
    assert BetRecorder(store).record(plans, "2026-10-11T10:00:00") == 3 + 1
    bets = store.read(names.BETS_TABLE).sort_values(names.COMBO)
    bets = bets[bets[names.RACE_ID] == "2026101105040401"]
    assert list(bets[names.TICKET_TYPE]) == ["単勝", "馬単", "馬単"] and set(bets[names.PARTICIPATION]) == {names.MATCH_WIN}
    assert list(bets[names.STAKE_YEN]) == [3_700, 100, 100] and bets.iloc[1][names.BOUGHT_ODDS] == pytest.approx(30.0)


def _combo_forecast(rid: str, timing: str = "当日") -> dict:
    """組の期待値のワイド2点・馬単2点（1点はトリガミで外した）・3連複1点があるレース。期待度は「低」で、◎ の単勝・馬単は買わない。"""
    forecast = _forecast(rid, "1勝クラス", [1.0, 1.0, 1.0, 1.0])
    forecast.update(timing=timing, expectation="低", tickets=[
        {"rule": "ワイド（組の期待値）", "ticket_type": "ワイド", "combo": "0102", "label": "1-2", "value": 1.05, "odds": 8.0, "dropped": ""},
        {"rule": "ワイド（組の期待値）", "ticket_type": "ワイド", "combo": "0204", "label": "2-4", "value": 1.2, "odds": 20.0, "dropped": ""},
        {"rule": "馬単（組の期待値）", "ticket_type": "馬単", "combo": "0401", "label": "4→1", "value": 1.2, "odds": 25.0, "dropped": ""},
        {"rule": "馬単（組の期待値）", "ticket_type": "馬単", "combo": "0402", "label": "4→2", "value": 1.1, "odds": 1.0, "dropped": "トリガミ"},
        {"rule": "3連複（組の期待値）", "ticket_type": "3連複", "combo": "010204", "label": "1-2-4", "value": 1.3, "odds": 300.0, "dropped": ""},
    ])
    return forecast


def _combo_wallet(store: ReviewStore, tmp_path: Path, combo_yen: int = 1_000_000) -> Wallet:
    import json
    path = tmp_path / "財布.json"
    path.write_text(json.dumps({MATCH_WALLET: 100_000, POLICY_WALLET: 30_000, WIN_WALLET: 100_000, COMBO_WALLET: combo_yen}), encoding="utf-8")
    return Wallet(store, path)


def test_組の期待値の1点は組の期待値用の財布の券種ごとの割合で決め_既定の50万円なら馬単600円とワイド100円(store: ReviewStore, tmp_path: Path):
    day = date(2026, 10, 11)
    wallet = Wallet(store, tmp_path / "財布.json")
    assert [wallet.point_yen(label, day, COMBO_WALLET) for label in ("馬単", "ワイド", "3連複", "3連単")] == [600, 100, 0, 0]
    (tmp_path / "rich").mkdir()
    rich = _combo_wallet(store, tmp_path / "rich", 15_000_000)
    assert [rich.point_yen(label, day, COMBO_WALLET) for label in ("馬単", "ワイド", "3連複", "3連単")] == [18_000, 3_400, 1_000, 1_400]


def test_当日の予想は組の期待値の買い目を券種ごとの額で買い_100円に届かない券種と前日は買わない(store: ReviewStore, tmp_path: Path, con):
    planner = DayPlanner(_combo_wallet(store, tmp_path))
    plans = {plan.rid[-2:]: plan for plan in planner.plan(con, date(2026, 10, 11), [
        _combo_forecast("2026101105040401"), _combo_forecast("2026101105040402", timing="前日")])}
    bought = plans["01"]
    assert [(ticket.ticket_type, ticket.combo, ticket.yen, ticket.kind) for ticket in bought.tickets] == [
        ("ワイド", "0102", 200, names.MATCH_COMBO), ("ワイド", "0204", 200, names.MATCH_COMBO), ("馬単", "0401", 1_200, names.MATCH_COMBO)]
    assert bought.tickets[0].value == pytest.approx(1.05) and bought.ticket_yen == 1_600
    assert "組の期待値" in bought.ticket_reason and "3連複（組の期待値）は1点が 100円に届かない" in bought.ticket_reason
    assert plans["02"].tickets == () and not plans["02"].buys


def test_組の期待値用が止まりの線を割れば組の期待値の買い目を止め_記録は勝負組の期待値として書く(store: ReviewStore, tmp_path: Path, con):
    import pandas as pd
    planner = DayPlanner(_combo_wallet(store, tmp_path))
    plans = planner.plan(con, date(2026, 10, 11), [_combo_forecast("2026101105040401")])
    assert BetRecorder(store).record(plans, "2026-10-11T10:00:00") == 3 + 1   # その日1レースだけなので、ノルマ（日）の複勝1点も入る
    bets = store.read(names.BETS_TABLE)
    combos = bets[bets[names.PARTICIPATION] == names.MATCH_COMBO]
    assert list(combos[names.TICKET_TYPE]) == ["ワイド", "ワイド", "馬単"] and sorted(combos[names.STAKE_YEN]) == [200, 200, 1_200]
    store.write(names.BETS_TABLE, pd.DataFrame([
        {names.RACE_ID: "r1", names.TICKET_TYPE: "3連単", names.COMBO: "010203", names.RACE_DATE: date(2026, 9, 20),
         names.PARTICIPATION: names.MATCH_COMBO, names.RECORD_ONLY: False, names.STAKE_YEN: 400_000, names.PAYOUT_YEN: 0, names.SETTLED: True},
    ]))
    stopped = planner.plan(con, date(2026, 10, 11), [_combo_forecast("2026101105040401")])[0]
    assert stopped.tickets == () and "70%" in stopped.ticket_reason
