"""1つの出どころの確率で、元と同じ買い方を当てる。"""

from __future__ import annotations

import pandas as pd

from ..backtest import PlaceLineChoice, YearlyPaybackTable
from .source_result import SourceResult

#: 買った馬券の表に残す列。
_TICKET_COLUMNS = ("rid", "horse_no", "year", "day", "win_odds", "placed", "place_payout")


class ProbabilitySourceBacktest:
    """1つの出どころの確率に、元と同じ買い方の決まりを当てて成績を出す。

    期待値 = 確率 × 想定払戻倍率。線は候補（1.00〜1.40）から前半（2019〜2021年）だけで決まりどおりに選び
    （``PlaceLineChoice``）、選んだ線以上の買い目を1点 100円で買う。年ごとの回収率と幅は ``YearlyPaybackTable``。
    確率の出どころだけが違い、ほかは ``backtest.py`` と同じ。
    """

    def __init__(self, line_choice: PlaceLineChoice | None = None, yearly: YearlyPaybackTable | None = None) -> None:
        self._line_choice = line_choice or PlaceLineChoice()
        self._yearly = yearly or YearlyPaybackTable()

    def run(self, table: pd.DataFrame, source: str) -> SourceResult:
        """``table`` は ``ProbabilitySourceTable`` の表、``source`` は確率の列の名前。"""
        expected_value = table[source] * table["想定払戻倍率"]
        tickets = pd.DataFrame({"rid": table["rid"], "year": table["year"], "day": table["day"],
                                "ev": expected_value, "payout": table["place_payout"]})
        study = self._line_choice.run(tickets)
        bought = self._bought(table, expected_value, study)
        return SourceResult(source, study, bought, self._yearly.build(bought))

    def _bought(self, table: pd.DataFrame, expected_value: pd.Series, study) -> pd.DataFrame:
        if study.chosen is None:
            return table.iloc[0:0][list(_TICKET_COLUMNS)].reset_index(drop=True)
        rows = expected_value.notna() & (expected_value >= study.chosen.line)
        return table.loc[rows, list(_TICKET_COLUMNS)].reset_index(drop=True)
