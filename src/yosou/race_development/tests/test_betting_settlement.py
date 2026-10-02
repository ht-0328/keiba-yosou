"""契約: 買い目は払戻の表の同じ組番の払戻金で精算し（同着はそれぞれの行）、不成立・特払の券種と払戻の無いレースは
見送る（表から落とす）。回収率は買い方 × 券種 × 年と合計で、的中率は当たったレース ÷ 買ったレース。
"""

import pandas as pd
import pytest

from yosou.race_development.betting import TOTAL_YEAR, ReturnSummary, TicketSettler
from yosou.race_development.betting.column_names import COMBO, HIT, PAYOUT, RACE_ID, RULE, STAKE, TICKET_TYPE, YEAR, YEN
from yosou.shared.betting import TicketType
from yosou.shared.repository import REFUNDED, void_column

RACE_1, RACE_2, RACE_3, RACE_4 = "2025070605010101", "2025070605010102", "2025070605010103", "2025070605010104"


def tickets(rows: list[tuple[str, str, str]], rule: str = "印どおり（モデル）") -> pd.DataFrame:
    return pd.DataFrame([{RACE_ID: race, TICKET_TYPE: kind, COMBO: combo, STAKE: 100, RULE: rule} for race, kind, combo in rows])


def flags(void_races: dict[TicketType, list[str]]) -> pd.DataFrame:
    races = [RACE_1, RACE_2, RACE_3]
    table = pd.DataFrame({RACE_ID: races, REFUNDED: False})
    for ticket_type in TicketType:
        table[void_column(ticket_type)] = [race in void_races.get(ticket_type, []) for race in races]
    return table


PAYOUTS = {
    # RACE_1 は 1着同着（馬番 3 と 8）で、単勝の払戻が2行ある。
    TicketType.WIN: pd.DataFrame({RACE_ID: [RACE_1, RACE_1, RACE_2], COMBO: ["03", "08", "05"], YEN: [410, 1230, 250]}),
    TicketType.WIDE: pd.DataFrame({RACE_ID: [RACE_1] * 3, COMBO: ["0308", "0305", "0508"], YEN: [300, 550, 1210]}),
}


def test_dead_heat_pays_each_matching_row_and_misses_pay_zero():
    bought = tickets([(RACE_1, "win", "03"), (RACE_1, "win", "08"), (RACE_1, "win", "01"), (RACE_1, "wide", "0508")])
    settled = TicketSettler().settle(bought, PAYOUTS, flags({}))
    assert list(settled[PAYOUT]) == [410, 1230, 0, 1210]
    assert list(settled[HIT]) == [True, True, False, True]


def test_void_ticket_type_and_races_without_payout_are_skipped():
    bought = tickets([(RACE_2, "win", "05"), (RACE_2, "wide", "0105"), (RACE_3, "win", "01"), (RACE_4, "win", "01")])
    settled = TicketSettler().settle(bought, PAYOUTS, flags({TicketType.WIDE: [RACE_2]}))
    # RACE_2 のワイドは不成立で見送り、RACE_4 は払戻のデータが無いので見送り。RACE_3 は外れ（0円）で残る。
    assert list(zip(settled[RACE_ID], settled[TICKET_TYPE])) == [(RACE_2, "win"), (RACE_3, "win")]
    assert list(settled[PAYOUT]) == [250, 0]


def test_return_summary_by_rule_ticket_type_and_year():
    settled = pd.DataFrame({
        RACE_ID: ["a", "a", "b", "c", "d", "d"],
        TICKET_TYPE: ["quinella", "quinella", "quinella", "quinella", "win", "win"],
        COMBO: ["0102", "0103", "0102", "0102", "01", "02"],
        STAKE: 100, RULE: "印どおり（モデル）",
        PAYOUT: [0, 1500, 0, 600, 0, 0],
        HIT: [False, True, False, True, False, False],
        YEAR: [2024, 2024, 2024, 2025, 2025, 2025],
    })
    table = ReturnSummary().table(settled).set_index(["券種", "年"])
    assert list(table.index) == [("単勝", "2025"), ("単勝", TOTAL_YEAR), ("馬連", "2024"), ("馬連", "2025"), ("馬連", TOTAL_YEAR)]
    quinella_2024 = table.loc[("馬連", "2024")]
    assert (quinella_2024["買ったレース"], quinella_2024["点数"], quinella_2024["賭け金（円）"], quinella_2024["払戻（円）"]) == (2, 3, 300, 1500)
    assert quinella_2024["的中率"] == pytest.approx(0.5)
    assert quinella_2024["回収率"] == pytest.approx(5.0)
    assert quinella_2024["最大の払戻を除いた回収率"] == pytest.approx(0.0)
    total = table.loc[("馬連", TOTAL_YEAR)]
    assert (total["買ったレース"], total["点数"], total["払戻（円）"]) == (3, 4, 2100)
    assert total["的中率"] == pytest.approx(2 / 3)
    assert total["回収率"] == pytest.approx(2100 / 400)
    assert total["最大の払戻を除いた回収率"] == pytest.approx(600 / 400)
    assert table.loc[("単勝", TOTAL_YEAR)]["回収率"] == 0.0
