"""レースの側の型ごとに、人気薄が勝ったレースの割合と、人気薄の勝ちのうちどれだけがその型のレースだったかを並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.race_type_catalog import RACE_TYPES
from .cells import percent, ratio


@dataclass(frozen=True)
class RaceTypeTable:
    """``races`` は ``RaceTable`` の表。"""

    def build(self, races: pd.DataFrame, title: str) -> Table:
        won_total = int(races["longshot_won"].sum())
        rows = [self._row(rule.name, rule.description, rule.flags(races), races, won_total) for rule in RACE_TYPES]
        rows.append(self._row("（全部）", "", pd.Series(True, index=races.index), races, won_total))
        columns = ["レースの型", "定義", "レース数", "レースの中の割合", "人気薄が勝った", "人気薄が勝つ割合", "人気薄の勝ちのうちこの型", "実際 ÷ 市場"]
        return Table(columns, rows, title=title,
                     note="実際 ÷ 市場 は、人気薄が勝ったレース数 ÷ そのレースたちの10番人気以下のオッズから見た勝率の合計。")

    @staticmethod
    def _row(name: str, description: str, flag: pd.Series, races: pd.DataFrame, won_total: int) -> list[object]:
        chosen = races.loc[flag]
        won = int(chosen["longshot_won"].sum())
        return [name, description, len(chosen), percent(len(chosen), len(races)), won, percent(won, len(chosen)),
                percent(won, won_total), ratio(won, chosen["longshot_market"].sum())]
