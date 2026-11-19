"""2つのモデルの値から、買う馬（単勝と、1着に固定した 3連単の軸）を選ぶ決まり。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .late_columns import HORSE_NO, LIKENESS, ODDS_NOW, PAYBACK
from .late_pick import LatePick

#: 買う馬らしさの線・戻りの見込みの線・3連単の相手の頭数（研究「地方の直前の材料で買う」で決めた値）。
LIKENESS_LINE = 0.4
PAYBACK_LINE = 0.95
OPPONENTS = 5


@dataclass(frozen=True)
class LateRule:
    """2つがそろって線以上の馬だけを買う。相手は、その馬を除いた、決めたときの単勝オッズの低い順（同じオッズなら馬番の若い順）。"""

    likeness_line: float = LIKENESS_LINE
    payback_line: float = PAYBACK_LINE
    opponents: int = OPPONENTS

    def chosen(self, scored: pd.DataFrame) -> pd.DataFrame:
        """線を満たす行（何レースぶんでもよい）。"""
        return scored[(scored[LIKENESS] >= self.likeness_line) & (scored[PAYBACK] >= self.payback_line)]

    def closeness(self, race: pd.DataFrame) -> float | None:
        """1レースぶんの表の「線への近さ」: 馬ごとに 2つの値をそれぞれの線で割った小さいほうを取り、その中でいちばん大きい値。
        1 以上なら、2つがそろって線以上の馬（買う馬）がいる。地方の期待度の点数に使う。馬がいなければ None。"""
        return None if race.empty else float(self.ratios(race).max())

    def ratios(self, scored: pd.DataFrame) -> pd.Series:
        """馬ごとの、買う馬らしさ ÷ その線 と 戻りの見込み ÷ その線 の小さいほう（1 以上なら買う馬）。"""
        return pd.concat([scored[LIKENESS] / self.likeness_line, scored[PAYBACK] / self.payback_line], axis=1).min(axis=1)

    def picks(self, race: pd.DataFrame) -> list[LatePick]:
        """1レースぶんの表から、買う馬（買う馬らしさの高い順）。いなければ空。"""
        order = race.sort_values([ODDS_NOW, HORSE_NO])[HORSE_NO].astype(int).tolist()
        chosen = self.chosen(race).sort_values(LIKENESS, ascending=False)
        return [self._pick(row, order) for _, row in chosen.iterrows()]

    def _pick(self, row: pd.Series, order: list[int]) -> LatePick:
        axis = int(row[HORSE_NO])
        opponents = tuple(no for no in order if no != axis)[:self.opponents]
        return LatePick(axis, float(row[ODDS_NOW]), float(row[LIKENESS]), float(row[PAYBACK]), opponents)
