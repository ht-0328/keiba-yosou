"""HighPayoutPicker（高配当の買い目を作る）と、今週の予想の買い目（``ForecastTickets``）に足したときのテスト。

予想のパッケージ（``yosou.high_payout_combos``）は使わず、約束どおりの形の偽物（確率を出す部品と買い目の決まり）を渡す。値は架空。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 今週の予想.forecast_tickets import TICKET_KEYS, ForecastTickets
from 今週の予想.high_payout_picker import HORSE_COLUMNS, HighPayoutPicker
from 今週の予想.mark_tickets import COLUMNS
from 今週の予想.tests.fake_high_payout_predictor import FakeHighPayoutPredictor
from 今週の予想.tests.fake_high_payout_rule import HIGH_LINE, FakeHighPayoutRule
from 今週の予想.tests.test_weekly_tickets import _marked_race
from 今週の予想.ticket_rules import HIGH_PAYOUT_LABELS, HIGH_PAYOUT_MAX_POINTS, HIGH_PAYOUT_TICKET_TYPES, HIGH_PAYOUT_VALUE_LINE
from 今週の予想.torigami_filter import DROPPED, TORIGAMI, TorigamiFilter

#: 予想のある5券種の全部（本番で出していない券種も入れて確かめるとき）。
ALL_TYPES: tuple[TicketType, ...] = tuple(HIGH_PAYOUT_LABELS)


def _board(odds: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({"race_id": "R", "combo": list(odds), "odds": list(odds.values())})


def _boards() -> dict[TicketType, pd.DataFrame]:
    """ワイドは 3-8（20倍）・1-3（5倍）・5-9（40倍）・3-9（30倍）、馬連は 3-8（50倍）、3連単は 3→1→8（600倍）。"""
    return {TicketType.WIDE: _board({"0308": 20.0, "0103": 5.0, "0509": 40.0, "0309": 30.0}),
            TicketType.QUINELLA: _board({"0308": 50.0}), TicketType.TRIFECTA: _board({"030108": 600.0})}


def _picker(**changes) -> HighPayoutPicker:
    """確率は 3-8 が 0.10、1-3 が 0.50、5-9 が 0.02、3-9 が 0.05、3→1→8 が 0.002。期待値はワイド 3-8 が 2.0・1-3 が 2.5（線より安い）・
    5-9 が 0.8・3-9 が 1.5、馬連 3-8 が 5.0、3連単 3→1→8 が 1.2。対象の券種と上限の点数は、渡さなければ本番の決まり。"""
    predictor = FakeHighPayoutPredictor({"0308": 0.10, "0103": 0.50, "0509": 0.02, "0309": 0.05, "030108": 0.002})
    lines = {ticket_type: HIGH_LINE for ticket_type in HIGH_PAYOUT_LABELS}
    return HighPayoutPicker(predictor, FakeHighPayoutRule(changes.get("max_points", HIGH_PAYOUT_MAX_POINTS)), lines, **changes)


def _by_rule(picks: pd.DataFrame) -> dict[str, list[str]]:
    return {rule: sorted(group["combo"]) for rule, group in picks.groupby("rule")}


def test_高配当の線以上で期待値が線以上の組を_買い目の形で返す() -> None:
    picker = _picker()
    picks = picker.pick(_marked_race(), _boards())
    assert list(picks.columns) == list(COLUMNS)
    # 本番の対象の券種（ワイド・馬連・馬単・3連複）だけ。3連単は期待値が線以上でも出さない
    assert _by_rule(picks) == {"ワイド（高配当）": ["0308", "0309"], "馬連（高配当）": ["0308"]}
    assert _by_rule(_picker(ticket_types=ALL_TYPES).pick(_marked_race(), _boards())) == {"ワイド（高配当）": ["0308", "0309"], "馬連（高配当）": ["0308"], "3連単（高配当）": ["030108"]}
    assert (picks["stake_units"] == 1.0).all() and (picks["race_id"] == "R").all() and (picks["win_value_band"] == "1.00 以上").all()
    wide = picks[picks["rule"] == "ワイド（高配当）"].set_index("combo")
    assert wide.loc["0308", "value"] == pytest.approx(2.0) and wide.loc["0308", "ticket_type"] == "ワイド"
    # 予想には、約束の列だけを渡す（印を付けた表に無い列は欠損値）
    assert list(picker._predictor.horses.columns) == list(HORSE_COLUMNS) and picker._predictor.horses["is_danger"].isna().all()
    assert picker.ready and picker.needed() == tuple(HIGH_PAYOUT_LABELS)
    assert picker.conditions() == {"ready": True, "value_line": HIGH_PAYOUT_VALUE_LINE, "max_points": HIGH_PAYOUT_MAX_POINTS,
                                   "high_lines": {ticket_type.label: HIGH_LINE for ticket_type in HIGH_PAYOUT_TICKET_TYPES}}


def test_板が足りなくて予想が組を返さなければ_0点で誤りにしない() -> None:
    boards = {TicketType.WIDE: _boards()[TicketType.WIDE]}   # 3連単の板が無い
    picks = _picker().pick(_marked_race(), boards)
    assert picks.empty and list(picks.columns) == list(COLUMNS)
    assert _picker().pick(_marked_race(), {}).empty


def test_学習済みモデルの置き場所が無ければ_買い目を作らない部品になる(tmp_path: Path) -> None:
    for picker in (HighPayoutPicker.load(tmp_path / "無い"), HighPayoutPicker.load(None), HighPayoutPicker(None, None)):
        assert not picker.ready and picker.needed() == ()
        assert picker.pick(_marked_race(), _boards()).empty
        assert picker.conditions()["ready"] is False and picker.conditions()["high_lines"] == {}


def test_上限の点数があれば_券種ごとに確率の高い順に残す() -> None:
    picks = _picker(max_points=1, ticket_types=ALL_TYPES).pick(_marked_race(), _boards())
    # ワイドは確率の高い 3-8（0.10）だけ。3-9（0.05）は落ちる
    assert _by_rule(picks) == {"ワイド（高配当）": ["0308"], "馬連（高配当）": ["0308"], "3連単（高配当）": ["030108"]}
    assert _picker(max_points=1).conditions()["max_points"] == 1


def test_対象の券種だけを残し_評価できない馬を含む組は落とす() -> None:
    only_wide = _picker(ticket_types=(TicketType.WIDE,))
    assert _by_rule(only_wide.pick(_marked_race(), _boards())) == {"ワイド（高配当）": ["0308", "0309"]}
    assert only_wide.conditions()["high_lines"] == {"ワイド": HIGH_LINE}
    assert only_wide.needed() == tuple(HIGH_PAYOUT_LABELS)   # ほかの券種の板も予想の材料に使うので、読む板は減らさない
    marked = _marked_race()
    unrated = marked.assign(unrated=marked["horse_no"] == 8)   # 8番が評価できない馬
    assert _by_rule(_picker().pick(unrated, _boards())) == {"ワイド（高配当）": ["0309"]}


def test_実物の買い目の決まりでも_同じ呼び方で買い目になる() -> None:
    try:
        from yosou.high_payout_combos import DEFAULT_BANDS, HighPayoutRule
    except ImportError:
        pytest.skip("予想のパッケージ（yosou.high_payout_combos）がまだ読み込めない")
    predictor = FakeHighPayoutPredictor({"0308": 0.10, "0103": 0.50, "0509": 0.02, "0309": 0.05, "030108": 0.002})
    lines = {ticket_type: band.high_line for ticket_type, band in DEFAULT_BANDS.items()}
    # 実物も、期待値の線と上限の点数は作るときに渡し、pick には組の表だけを渡す
    picker = HighPayoutPicker(predictor, HighPayoutRule(DEFAULT_BANDS, HIGH_PAYOUT_VALUE_LINE), lines, ticket_types=ALL_TYPES)
    # 実物の帯はワイド 10倍・馬連 30倍・3連単 500倍以上。偽物の線（どれも 10倍）のときと同じ組が残る
    assert _by_rule(picker.pick(_marked_race(), _boards())) == {"ワイド（高配当）": ["0308", "0309"], "馬連（高配当）": ["0308"], "3連単（高配当）": ["030108"]}
    capped = HighPayoutPicker(predictor, HighPayoutRule(DEFAULT_BANDS, HIGH_PAYOUT_VALUE_LINE, 1), lines, max_points=1)
    assert _by_rule(capped.pick(_marked_race(), _boards()))["ワイド（高配当）"] == ["0308"]
    assert picker.conditions()["high_lines"] == {ticket_type.label: DEFAULT_BANDS[ticket_type].high_line for ticket_type in ALL_TYPES}


def test_複勝オッズの最高は_渡した複勝オッズで埋めて予想に渡す() -> None:
    """当日の予想の表には複勝オッズ（最高）の列が無い。予想は最低と最高の両方を材料に学んでいるので、欠けたまま渡さない。"""
    picker = _picker()
    marked = _marked_race().drop(columns=["place_odds_high"], errors="ignore")
    numbers = [int(number) for number in marked["horse_no"]]
    picker.pick(marked, _boards())
    assert picker._predictor.horses["place_odds_high"].isna().all()   # 複勝オッズを渡さなければ欠損値のまま
    place = pd.DataFrame({"race_id": "R", "horse_no": numbers, "place_odds_low": 1.5, "place_odds_high": [2.0 + number for number in numbers]})
    picks = picker.pick(marked, _boards(), place)
    assert picker._predictor.horses.set_index("horse_no")["place_odds_high"].to_dict() == {number: 2.0 + number for number in numbers}
    assert _by_rule(picks) == {"ワイド（高配当）": ["0308", "0309"], "馬連（高配当）": ["0308"]}
    # 表に値があればそれを使い、複勝オッズの表に無い馬は欠損値のまま
    picker.pick(marked.assign(place_odds_high=9.9), _boards(), place)
    assert (picker._predictor.horses["place_odds_high"] == 9.9).all()
    picker.pick(marked, _boards(), place.iloc[:1])
    assert picker._predictor.horses["place_odds_high"].notna().sum() == 1


def test_高配当の買い目はトリガミの確かめをしない() -> None:
    tickets = pd.DataFrame({"race_id": "R", "rule": ["ワイド（高配当）"] * 3 + ["ワイド"] * 3, "odds": [2.0, 2.5, 30.0] * 2})
    dropped = TorigamiFilter().apply(tickets)[DROPPED].tolist()
    # ふつうのワイドは、3点のうち 2.0倍が投資（3点）以下なので外す（残り2点は 2.5倍 > 2点で買う）。高配当の買い目は同じオッズでも外さない
    assert dropped == ["", "", "", TORIGAMI, "", ""]


def _race_day_db(tmp_path: Path) -> tuple[duckdb.DuckDBPyConnection, str]:
    """締め切り前の断面: ワイド 3-8 が 20.0倍・1-3 が 5.0倍、3連単 3→1→8 が 600.0倍、複勝は 3番が 1.5〜2.1倍・8番が 4.0〜6.2倍。"""
    from 共通 import keys
    from 合成DB import synth

    sample = synth.simple_race()
    ra = sample.ra[0]
    at = "04061200"
    sample.odds.append(("o3", synth.odds_header(ra, "o3", stage="1", announced=at)))
    sample.odds.append(("o3__ワイドオッズ", synth.range_odds_row(ra, "o3__ワイドオッズ", "0308", 200, 240, announced=at)))
    sample.odds.append(("o3__ワイドオッズ", synth.range_odds_row(ra, "o3__ワイドオッズ", "0103", 50, 60, seq=2, announced=at)))
    sample.odds.append(("o1", synth.odds_header(ra, "o1", stage="1", announced=at)))
    sample.odds.append(("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", "03", 15, 21, announced=at)))
    sample.odds.append(("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", "08", 40, 62, seq=2, announced=at)))
    sample.odds.append(("o6", synth.odds_header(ra, "o6", stage="1", announced=at)))
    sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "030108", 6000, announced=at)))
    con = duckdb.connect(str(synth.build_db(tmp_path / "high.duckdb", sample)), read_only=True)
    return con, "".join(ra[column] for column in keys.RACE_KEY)


def test_当日の予想の買い目に高配当の買い目を足し_ほかの買い目は変えない(tmp_path: Path) -> None:
    con, race_id = _race_day_db(tmp_path)
    marked = _marked_race()
    plain = ForecastTickets().build(con, race_id, marked, "1.00 以上", odds_known=True, race_day=True)
    every = _picker(ticket_types=ALL_TYPES)   # 3連単も出す部品（JSON の形を3頭の組でも確かめる）
    tickets = ForecastTickets(high_payout=every).build(con, race_id, marked, "1.00 以上", odds_known=True, race_day=True)
    high = [ticket for ticket in tickets if ticket["rule"] in HIGH_PAYOUT_LABELS.values()]
    assert all(tuple(ticket) == TICKET_KEYS for ticket in tickets)
    assert [(ticket["rule"], ticket["ticket_type"], ticket["combo"], ticket["label"], ticket["horses"]) for ticket in high] == [
        ("ワイド（高配当）", "ワイド", "0308", "3-8", [3, 8]), ("3連単（高配当）", "3連単", "030108", "3→1→8", [3, 1, 8])]
    wide, trifecta = high
    assert wide["odds"] == 20.0 and wide["value"] == pytest.approx(2.0) and wide["probability"] == pytest.approx(0.10) and wide["dropped"] == ""
    assert trifecta["odds"] == 600.0 and trifecta["value"] == pytest.approx(1.2) and trifecta["stake_units"] == 1.0
    # 予想に渡す馬ごとの表の複勝オッズ（最高）は、締め切り前の複勝オッズで埋まる（複勝オッズの無い馬は欠損値のまま）
    passed = every._predictor.horses.set_index("horse_no")["place_odds_high"]
    assert passed[3] == pytest.approx(2.1) and passed[8] == pytest.approx(6.2) and passed.drop([3, 8]).isna().all()
    # 本番の決まりの部品（3連単は対象でない）は、ワイドだけを足す
    usual = ForecastTickets(high_payout=_picker()).build(con, race_id, marked, "1.00 以上", odds_known=True, race_day=True)
    assert [ticket["rule"] for ticket in usual if ticket["rule"] in HIGH_PAYOUT_LABELS.values()] == ["ワイド（高配当）"]
    # ほかの買い目は、高配当の買い目を足す前と同じ
    assert [ticket for ticket in tickets if ticket["rule"] not in HIGH_PAYOUT_LABELS.values()] == plain
    assert not any(ticket["rule"] in HIGH_PAYOUT_LABELS.values() for ticket in plain)   # 部品を渡さなければ足さない
    # 当日の予想でなければ足さない
    before = ForecastTickets(high_payout=_picker()).build(con, race_id, marked, "1.00 以上", odds_known=True, race_day=False)
    assert not any(ticket["rule"] in HIGH_PAYOUT_LABELS.values() for ticket in before)
    # 学習済みモデルが無いときは、何も足さない
    missing = ForecastTickets(high_payout=HighPayoutPicker.load(tmp_path / "無い"))
    assert missing.build(con, race_id, marked, "1.00 以上", odds_known=True, race_day=True) == plain
    assert missing.high_payout_conditions()["ready"] is False
    assert ForecastTickets(high_payout=_picker()).high_payout_conditions()["ready"] is True


def test_期待値の線と予想の名前は_予想のパッケージと同じ() -> None:
    try:
        from yosou.high_payout_combos import DEFAULT_BANDS, DEFAULT_VALUE_LINE, YOSOU_NAME
    except ImportError:
        pytest.skip("予想のパッケージ（yosou.high_payout_combos）がまだ読み込めない")
    from 今週の予想.model_folders import HIGH_PAYOUT_YOSOU_NAME

    assert HIGH_PAYOUT_VALUE_LINE == DEFAULT_VALUE_LINE
    assert HIGH_PAYOUT_YOSOU_NAME == YOSOU_NAME
    assert set(HIGH_PAYOUT_LABELS) == set(DEFAULT_BANDS)


def test_本番の決まりは_3連単を除いた4券種で_1券種10点まで() -> None:
    assert HIGH_PAYOUT_TICKET_TYPES == (TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA, TicketType.TRIO)
    assert HIGH_PAYOUT_MAX_POINTS == 10 and HIGH_PAYOUT_VALUE_LINE == 1.05
    assert set(HIGH_PAYOUT_TICKET_TYPES) < set(HIGH_PAYOUT_LABELS)   # 対象から外した券種の、前に保存した予想も読める
