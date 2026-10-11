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
from 今週の予想.wallet import MATCH_WALLET, POLICY_WALLET, Wallet


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
    assert wallet.initial() == {MATCH_WALLET: 100_000, POLICY_WALLET: 30_000}
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
