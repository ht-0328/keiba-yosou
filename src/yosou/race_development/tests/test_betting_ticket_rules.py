"""契約: 印どおりの買い目は券種ごとに決まった点数（設計書 16 の 8.）で、印が足りなければ組める買い目だけ。
期待値の買い目は、当たる確率 × 確定オッズ（複勝・ワイドは最低）が線以上の組番を全部。組番は払戻の表と同じ形。
"""

import pandas as pd
import pytest

from yosou.race_development.betting import MODEL_MARK_RULE, ExpectedValueTicketRule, MarkTicketRule, Ticket
from yosou.race_development.betting.column_names import (
    COMBO,
    EXPECTED_VALUE,
    HORSE_NO,
    MARK,
    ODDS,
    PROBABILITY,
    RACE_ID,
    RULE,
    STAKE,
    TICKET_TYPE,
)
from yosou.shared.betting import TicketType

RACE = "2025070605010101"


def marks(pairs: dict[int, str]) -> pd.DataFrame:
    return pd.DataFrame({HORSE_NO: list(pairs), MARK: list(pairs.values())})


#: ◎ 12・○ 3・▲ 7・△ 1。☆ 5 と 注 9 は買い目に使わない。
FULL = marks({12: "◎", 3: "○", 7: "▲", 1: "△", 5: "☆", 9: "注", 4: ""})


def test_ticket_combo_is_zero_padded_and_sorted_when_unordered():
    assert Ticket(RACE, TicketType.TRIO, (12, 1, 5), "x").combo == "010512"
    assert Ticket(RACE, TicketType.TRIFECTA, (12, 1, 5), "x").combo == "120105"
    assert Ticket(RACE, TicketType.WIN, (3,), "x").combo == "03"
    with pytest.raises(ValueError):
        Ticket(RACE, TicketType.QUINELLA, (3, 3), "x")


@pytest.mark.parametrize(("ticket_type", "combos"), [
    (TicketType.WIN, ["12"]),
    (TicketType.PLACE, ["12"]),
    (TicketType.WIDE, ["0312", "0712"]),
    (TicketType.QUINELLA, ["0312", "0712", "0112"]),
    (TicketType.EXACTA, ["1203", "1207", "1201"]),
    (TicketType.TRIO, ["030712", "010312", "010712"]),
    (TicketType.TRIFECTA, ["120307", "120301", "120703", "120701"]),
])
def test_mark_tickets_follow_the_table(ticket_type, combos):
    tickets = MarkTicketRule().tickets(RACE, FULL, ticket_type)
    assert list(tickets[COMBO]) == combos
    assert set(tickets[TICKET_TYPE]) == {ticket_type.key} and set(tickets[STAKE]) == {100}
    assert set(tickets[RULE]) == {MODEL_MARK_RULE} and set(tickets[RACE_ID]) == {RACE}


def test_mark_tickets_only_what_the_marks_allow():
    three = marks({12: "◎", 3: "○", 7: "▲"})
    rule = MarkTicketRule("印どおり（人気順）")
    assert list(rule.tickets(RACE, three, TicketType.QUINELLA)[COMBO]) == ["0312", "0712"]
    assert list(rule.tickets(RACE, three, TicketType.TRIFECTA)[COMBO]) == ["120307", "120703"]
    empty = rule.tickets(RACE, marks({}), TicketType.WIN)
    assert empty.empty and list(empty.columns) == [RACE_ID, TICKET_TYPE, COMBO, STAKE, RULE]


def test_expected_value_tickets_use_the_lowest_odds_and_the_line():
    probabilities = pd.DataFrame({RACE_ID: [RACE] * 4, COMBO: ["0102", "0103", "0203", "0104"], PROBABILITY: [0.30, 0.20, 0.10, 0.05]})
    # ワイドの確定オッズ: odds が最低、odds_high が最高。0103 は最高なら 1.1 だが、最低の 0.98 で見るので買わない。
    # 0104 は取消でオッズが無いので買わない。
    odds = pd.DataFrame({RACE_ID: [RACE] * 3, COMBO: ["0102", "0103", "0203"], ODDS: [3.5, 4.9, 12.0], "odds_high": [4.0, 5.5, 14.0]})
    tickets = ExpectedValueTicketRule().tickets(probabilities, odds, TicketType.WIDE)
    assert list(tickets[COMBO]) == ["0102", "0203"]
    assert list(tickets[EXPECTED_VALUE]) == pytest.approx([1.05, 1.2])
    assert set(tickets[TICKET_TYPE]) == {"wide"} and set(tickets[RULE]) == {"期待値 1.0 以上（モデル）"}
    assert ExpectedValueTicketRule(line=1.5).tickets(probabilities, odds, TicketType.WIDE).empty
