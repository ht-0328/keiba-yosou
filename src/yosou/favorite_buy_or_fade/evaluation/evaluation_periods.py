"""評価の年を、方針を決める年と確かめる年に分ける。"""

from __future__ import annotations

import pandas as pd

#: 方針（線・k・重みなど）を比べて決めるのに見てよい年。
TUNE = "方針を決める年"
#: 方針を決めたあと、その方針のまま成績を確かめる年。方針を決めるときには見ない。
CHECK = "確かめる年"


class EvaluationPeriods:
    """評価の年のうち、``tune_last_year`` までを「方針を決める年」、その次の年からを「確かめる年」にする（設計書 16 の 6）。

    方針を決める年だけを見て方針を選び、確かめる年でその方針のまま成績が保てるかを見る。
    確かめる年を見て方針を選び直すと、確かめる年も未知のデータではなくなる。
    """

    def __init__(self, tune_last_year: int, year_column: str) -> None:
        self._tune_last_year = tune_last_year
        self._year = year_column

    def split(self, rows: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """期間の名前（方針を決める年・確かめる年の順）→ その期間の行。行の無い期間は入れない。"""
        is_tune = rows[self._year] <= self._tune_last_year
        parts = {self.label(TUNE, rows[is_tune]): rows[is_tune], self.label(CHECK, rows[~is_tune]): rows[~is_tune]}
        return {name: part for name, part in parts.items() if not part.empty}

    def label(self, period: str, rows: pd.DataFrame) -> str:
        """期間の名前に、入っている年の範囲を添える（例 ``方針を決める年（2019〜2023年）``）。"""
        years = rows[self._year]
        return f"{period}（{years.min()}〜{years.max()}年）" if len(years) else period
