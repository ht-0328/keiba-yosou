"""勝ち馬の人気の分布の表（平地の全レースと WIN5 の対象レース）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent

#: この人気より下はまとめる。
_LAST = 16


@dataclass(frozen=True)
class WinnerPopularityTable:
    """``races`` は ``RaceTable`` の表。"""

    def build(self, races: pd.DataFrame) -> Table:
        win5 = races.loc[races["win5_leg"].notna()]
        flat_counts = self._counts(races)
        win5_counts = self._counts(win5)
        rows = [
            [label, int(flat_counts.get(label, 0)), percent(flat_counts.get(label, 0), len(races)),
             int(win5_counts.get(label, 0)), percent(win5_counts.get(label, 0), len(win5))]
            for label in flat_counts.index
        ]
        return Table(["勝ち馬の人気", "平地の全レース", "割合", "WIN5 の対象レース", "割合"], rows, title="3. 勝ち馬の人気")

    @staticmethod
    def _counts(races: pd.DataFrame) -> pd.Series:
        labels = races["winner_popularity"].clip(upper=_LAST).astype(int).map(
            lambda pop: f"{pop}番人気" if pop < _LAST else f"{_LAST}番人気以下")
        order = [f"{pop}番人気" for pop in range(1, _LAST)] + [f"{_LAST}番人気以下"]
        return labels.value_counts().reindex(order, fill_value=0)
