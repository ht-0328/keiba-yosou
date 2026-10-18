"""組の期待値で選ぶ買い目（``ComboValuePicker``）。値は架空。"""

from __future__ import annotations

from itertools import permutations

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboBlendWeights

from 今週の予想.combo_value_picker import ComboValuePicker
from 今週の予想.combo_value_rule import ALL_RACES, HIGH_RACES, TOP_COMBOS, ComboValueRule
from 今週の予想.mark_tickets import COLUMNS, RULE

#: 市場だけを信じる重み（組の確率 = その券種のオッズの逆数をそろえた値）。
_MARKET_ONLY = ComboBlendWeights(1.0, 0.0, 0.0, 0.0)


def _marked(race_id: str, expectation: str) -> pd.DataFrame:
    return pd.DataFrame({"race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "fold": "", "expectation": expectation,
                         "horse_no": [1, 2, 3], "probability": 1.0, "market_top3": 1.0, "win_probability": [0.5, 0.3, 0.2],
                         "market_win": [0.5, 0.3, 0.2]})


def _boards(race_ids: list[str]) -> dict[TicketType, pd.DataFrame]:
    """3連単は6組とも 6倍。馬連は 1-2 が 2倍・1-3 が 4倍・2-3 が 400倍（オッズの逆数の合計が 1 より小さいので、
    市場だけの重みでも、どの組も期待値が 1 を超える）。"""
    trifecta = pd.DataFrame([{"race_id": rid, "combo": "".join(f"{no:02d}" for no in order), "odds": 6.0}
                             for rid in race_ids for order in permutations((1, 2, 3))])
    quinella = pd.DataFrame([{"race_id": rid, "combo": combo, "odds": odds}
                             for rid in race_ids for combo, odds in (("0102", 2.0), ("0103", 4.0), ("0203", 400.0))])
    return {TicketType.TRIFECTA: trifecta, TicketType.QUINELLA: quinella}


def test_線以上で上限以下の組だけを買い_期待度高だけのルールはほかのレースを落とす() -> None:
    # オッズの逆数の合計は 0.5 + 0.25 + 0.0025 = 0.7525。確率は 0.664・0.332・0.003、期待値は 1.33・1.33・1.33
    rules = (ComboValueRule(TicketType.QUINELLA, ALL_RACES, 1.1, 100, adopted=True),)
    marked = pd.concat([_marked("r1", "高"), _marked("r2", "低")], ignore_index=True)
    tickets = ComboValuePicker(rules, {TicketType.QUINELLA: _MARKET_ONLY}).pick(marked, _boards(["r1", "r2"]))
    assert list(tickets.columns) == list(COLUMNS)
    assert sorted(zip(tickets["race_id"], tickets["combo"])) == [("r1", "0102"), ("r1", "0103"), ("r2", "0102"), ("r2", "0103")]   # 400倍は上限の外
    assert set(tickets[RULE]) == {"馬連（組の期待値）"} and (tickets["value"] > 1.3).all()
    high_only = (ComboValueRule(TicketType.QUINELLA, HIGH_RACES, 1.1, 1000, adopted=False),)
    tickets = ComboValuePicker(high_only, {TicketType.QUINELLA: _MARKET_ONLY}).pick(marked, _boards(["r1", "r2"]))
    assert sorted(tickets["combo"]) == ["0102", "0103", "0203"] and set(tickets["race_id"]) == {"r1"}


def test_重みか3連単の板が無い券種は0点で_要る板は重みのある券種と3連単だけ() -> None:
    rules = (ComboValueRule(TicketType.QUINELLA, ALL_RACES, 1.1, 100, adopted=True),
             ComboValueRule(TicketType.EXACTA, ALL_RACES, 1.1, 30, adopted=True))
    picker = ComboValuePicker(rules, {TicketType.QUINELLA: _MARKET_ONLY})
    assert picker.needed() == (TicketType.QUINELLA, TicketType.TRIFECTA)
    boards = _boards(["r1"])
    assert picker.pick(_marked("r1", "高"), {TicketType.QUINELLA: boards[TicketType.QUINELLA]}).empty   # 3連単の板が無い
    assert ComboValuePicker(rules, {}).needed() == ()


def test_本命を含む組だけのルールと_1レースの点数の上限() -> None:
    marked = _marked("r1", "高").assign(mark=["－", "◎", "－"])   # ◎ は 2番
    weights = {TicketType.QUINELLA: _MARKET_ONLY}
    top_only = (ComboValueRule(TicketType.QUINELLA, TOP_COMBOS, 1.1, 1000, adopted=True),)
    assert sorted(ComboValuePicker(top_only, weights).pick(marked, _boards(["r1"]))["combo"]) == ["0102", "0203"]
    capped = (ComboValueRule(TicketType.QUINELLA, ALL_RACES, 1.1, 1000, adopted=True, max_points=1),)
    tickets = ComboValuePicker(capped, weights).pick(marked, _boards(["r1"]))
    assert len(tickets) == 1   # 条件に合う 1-2・1-3・2-3 のうち、期待値の高い順に1点だけ


def test_区切りの重みに差し替えるのは直前1年の重みを使う券種だけ() -> None:
    rules = (ComboValueRule(TicketType.QUINELLA, ALL_RACES, 1.1, 100, adopted=True),
             ComboValueRule(TicketType.WIDE, ALL_RACES, 1.0, 100, adopted=True, rolling=True))
    picker = ComboValuePicker(rules, {TicketType.QUINELLA: _MARKET_ONLY, TicketType.WIDE: _MARKET_ONLY})
    other = ComboBlendWeights(0.5, 0.0, 0.0, 1.0)
    swapped = picker.with_weights({TicketType.QUINELLA: other, TicketType.WIDE: other})
    assert swapped._weights[TicketType.QUINELLA] == _MARKET_ONLY and swapped._weights[TicketType.WIDE] == other
