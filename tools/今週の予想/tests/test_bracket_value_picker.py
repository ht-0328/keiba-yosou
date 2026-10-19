"""枠連の組の期待値で選ぶ買い目（``BracketValuePicker``）と、券種の名前から券種を引く ``ticket_kind``。値は架空。"""

from __future__ import annotations

from itertools import combinations, permutations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import BRACKET, TicketType, ticket_kind
from yosou.shared.combo_value import BracketBlendWeights

from 今週の予想.bracket_value_picker import BracketValuePicker
from 今週の予想.combo_value_rule import ALL_RACES, HIGH_RACES, ComboValueRule
from 今週の予想.mark_tickets import COLUMNS, RULE, VALUE
from 今週の予想.race_condition import TOP3_SHARE, RaceCondition


def _marked(expectation: str = "高") -> pd.DataFrame:
    """4頭。1・2番が1枠、3・4番が2枠。◎ は 3番。"""
    return pd.DataFrame({"race_id": "R", "race_date": pd.Timestamp("2025-01-05"), "fold": "", "expectation": expectation,
                         "horse_no": [1, 2, 3, 4], "mark": ["○", "▲", "◎", "△"], "probability": 0.75, "market_top3": 0.75,
                         "win_probability": 0.25, "market_win": [0.4, 0.3, 0.2, 0.1]})


def _boards() -> dict[TicketType, pd.DataFrame]:
    """3連単は24組とも同じ 24倍。馬連は 1-2 が 2倍、ほかは 10倍。"""
    trifecta = pd.DataFrame([{"race_id": "R", "combo": "".join(f"{no:02d}" for no in order), "odds": 24.0}
                             for order in permutations((1, 2, 3, 4), 3)])
    quinella = pd.DataFrame([{"race_id": "R", "combo": f"{a:02d}{b:02d}", "odds": 2.0 if (a, b) == (1, 2) else 10.0}
                             for a, b in combinations((1, 2, 3, 4), 2)])
    return {TicketType.TRIFECTA: trifecta, TicketType.QUINELLA: quinella}


#: 枠連の板（1枠どうし・1枠と2枠・2枠どうし）。逆数の合計は 0.5 + 0.25 + 0.05 = 0.8 なので、枠連の市場だけの重みならどの組も期待値 1.25。
_BRACKET_BOARD = pd.DataFrame({"race_id": "R", "combo": ["11", "12", "22"], "odds": [2.0, 4.0, 20.0]})
_FRAMES = pd.DataFrame({"race_id": "R", "horse_no": [1, 2, 3, 4], "frame": [1, 1, 2, 2]})


def test_枠連の市場だけの重みなら_どの枠の組も期待値は逆数の合計の逆数() -> None:
    rule = ComboValueRule(BRACKET, ALL_RACES, 1.0, 1000, adopted=True)
    tickets = BracketValuePicker(rule, BracketBlendWeights(1.0, 0.0, 0.0, 0.0)).pick(_marked(), _boards(), _BRACKET_BOARD, _FRAMES)
    assert list(tickets.columns) == list(COLUMNS) and sorted(tickets["combo"]) == ["11", "12", "22"]
    assert set(tickets["ticket_type"]) == {"枠連"} and set(tickets[RULE]) == {"枠連（組の期待値）"}
    assert tickets[VALUE].tolist() == pytest.approx([1.25, 1.25, 1.25])


def test_馬連の市場の重みなら_枠の組の確率は馬の組の和() -> None:
    # 馬連の市場: 1-2 は 0.5 ÷ (0.5 + 5 × 0.1) = 0.5、ほかの5組は 0.1 ずつ。枠の組 1-2 は 1-3・1-4・2-3・2-4 の 0.4、1-1 は 1-2 の 0.5、2-2 は 3-4 の 0.1
    rule = ComboValueRule(BRACKET, ALL_RACES, 0.0, 1000, adopted=True)
    tickets = BracketValuePicker(rule, BracketBlendWeights(0.0, 1.0, 0.0, 0.0)).pick(_marked(), _boards(), _BRACKET_BOARD, _FRAMES)
    values = dict(zip(tickets["combo"], tickets[VALUE], strict=True))
    assert values["12"] == pytest.approx(0.4 * 4.0) and values["11"] == pytest.approx(0.5 * 2.0) and values["22"] == pytest.approx(0.1 * 20.0)


def test_期待度とレースの条件で絞り_重みが無ければ0点() -> None:
    rule = ComboValueRule(BRACKET, HIGH_RACES, 1.0, 1000, adopted=True)
    weights = BracketBlendWeights(1.0, 0.0, 0.0, 0.0)
    assert BracketValuePicker(rule, weights).pick(_marked("低"), _boards(), _BRACKET_BOARD, _FRAMES).empty
    # 市場の勝率の上位3頭の和は 0.4 + 0.3 + 0.2 = 0.9
    capped = ComboValueRule(BRACKET, ALL_RACES, 1.0, 1000, adopted=True, race_conditions=(RaceCondition(TOP3_SHARE, None, 0.62312, ""),))
    assert BracketValuePicker(capped, weights).pick(_marked(), _boards(), _BRACKET_BOARD, _FRAMES).empty
    assert BracketValuePicker(rule, None).pick(_marked(), _boards(), _BRACKET_BOARD, _FRAMES).empty
    assert not BracketValuePicker(rule, None).ready


def test_券種の名前から枠連か7つの券種を引く() -> None:
    assert ticket_kind("枠連") is BRACKET and BRACKET.spec.odds_table == "o1__枠連オッズ" and BRACKET.spec.payout_table == "hr__枠連払戻"
    assert ticket_kind("馬連") is TicketType.QUINELLA
    with pytest.raises(ValueError):
        ticket_kind("WIN5")
    assert np.isclose(BRACKET.spec.payout_rate, 0.775)
