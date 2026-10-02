"""契約: 期待値の線と券種の配分は、確かめる年より前の年の回収率だけで選び、その年に当てはめる（最初の年は選ばない）。
前の年までに決めた点数より少ない候補は選ばない。
"""

from __future__ import annotations

import pandas as pd

from ..betting import ValueLineChoice
from ..betting import value_line_choice as line
from ..betting.column_names import EXPECTED_VALUE, PAYOUT, RACE_ID, RULE, STAKE, TICKET_TYPE, YEAR

MARK, VALUE = "印どおり（モデル）", "期待値 1.0 以上（モデル）"


def settled_rows(year: str, rule: str, ticket_type: str, value: float, count: int, payout: int) -> list[dict[str, object]]:
    """同じ期待値の買い目を ``count`` 点。最初の1点だけ ``payout`` 円が当たる。"""
    return [{RACE_ID: f"{year}-{number}", TICKET_TYPE: ticket_type, RULE: rule, STAKE: 100, EXPECTED_VALUE: value,
             PAYOUT: payout if number == 0 else 0, YEAR: year} for number in range(count)]


def settled() -> pd.DataFrame:
    rows = []
    # 2021年: 単勝は期待値 2.5 の買い目だけが当たる（その線の回収率 150%）。印どおりは 50%。
    rows += settled_rows("2021", VALUE, "win", 1.1, 100, 0) + settled_rows("2021", VALUE, "win", 2.5, 100, 15000)
    rows += settled_rows("2021", MARK, "win", float("nan"), 100, 5000)
    # 2022年: 単勝は期待値 1.1 の買い目が当たり、2.5 の買い目は外れる。
    rows += settled_rows("2022", VALUE, "win", 1.1, 100, 30000) + settled_rows("2022", VALUE, "win", 2.5, 100, 0)
    rows += settled_rows("2022", MARK, "win", float("nan"), 100, 8000)
    # 数点だけの大当たり（点数が少ないので選ばれない）。
    rows += settled_rows("2021", VALUE, "trio", 5.0, 3, 90000) + settled_rows("2022", VALUE, "trio", 5.0, 3, 0)
    return pd.DataFrame(rows)


def test_line_is_chosen_from_earlier_years_only() -> None:
    choice = ValueLineChoice()
    chosen = choice.chosen_lines(choice.candidates(settled()))
    win_2022 = chosen[(chosen[line.TYPE_LABEL] == "単勝") & (chosen[line.YEAR_LABEL] == "2022")].iloc[0]
    assert win_2022[line.CHOSEN] in {"期待値 2.0 以上", "期待値 1.5 以上", "期待値 1.2 以上"}
    assert win_2022[line.STAKE_TOTAL] == 10000
    assert win_2022[line.PAYOUT_TOTAL] == 0
    assert "2021" not in set(chosen[line.YEAR_LABEL])


def test_few_prior_points_are_not_chosen() -> None:
    choice = ValueLineChoice()
    chosen = choice.chosen_lines(choice.candidates(settled()))
    assert "3連複" not in set(chosen[line.TYPE_LABEL])


def test_allocation_buys_the_best_earlier_candidate_or_those_over_break_even() -> None:
    choice = ValueLineChoice()
    table = choice.allocation(choice.candidates(settled())).set_index([line.POLICY, line.YEAR_LABEL])
    assert table.loc[(line.BEST_ONE, "2022"), line.CHOSEN].endswith("・単勝")
    assert "印どおり" not in table.loc[(line.OVER_BREAK_EVEN, "2022"), line.CHOSEN]
    assert table.loc[(line.BEST_ONE, "合計"), line.STAKE_TOTAL] == table.loc[(line.BEST_ONE, "2022"), line.STAKE_TOTAL]
