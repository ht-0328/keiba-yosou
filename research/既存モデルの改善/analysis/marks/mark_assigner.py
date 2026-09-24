"""3つの予想から、レースごとに印を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_ID

from ..combined.horse_columns import FORM_PROBABILITY, FORM_SHIFT
from .mark import MARK, Mark
from .mark_material import DANGER, LONGSHOT_PLACE_VALUE

#: 全頭の予想の3着以内の確率の順位 → 印（4〜6位が △ の3頭）。
_RANK_MARKS: dict[int, Mark] = {
    1: Mark.HONMEI, 2: Mark.TAIKOU, 3: Mark.TANANA, 4: Mark.RENSHITA, 5: Mark.RENSHITA, 6: Mark.RENSHITA,
}


class MarkAssigner:
    """1頭ごとの表（``MarkMaterial`` の値を持つ）に、レースごとの印を付ける。

    1. 消: 人気馬の危険度が ``exclude_line`` 以上の馬は、どの印にもしない（線が NaN なら消は無い）。
    2. ◎○▲△△△: 残りの馬を、全頭の予想の3着以内の確率の高い順に並べ、1位から6位までに付ける。
    3. ☆: 印の無い穴馬のうち、穴馬の複勝の期待値がいちばん高い馬。
    4. 注: 印の無い馬のうち、全頭の予想の上げ下げ（オッズの見立てより来ると見ている度合い）がいちばん大きい馬。
       上げ下げが 0 以下（オッズの見立てより来ないと見ている）なら付けない。

    例: 1番人気が消なら、2番目に確率の高い馬が ◎ に繰り上がる。
    """

    def __init__(self, exclude_line: float) -> None:
        self._exclude_line = exclude_line

    def assign(self, horses: pd.DataFrame) -> pd.DataFrame:
        """``horses`` に印の列（印の無い馬は欠損値）を足した表。"""
        excluded = self._excluded(horses)
        marks = pd.Series(None, index=horses.index, dtype=object)
        ranks = horses[~excluded].groupby(RACE_ID)[FORM_PROBABILITY].rank(method="first", ascending=False)
        marks[ranks.index] = ranks.map(lambda rank: _RANK_MARKS[int(rank)].value if int(rank) in _RANK_MARKS else None)
        marks = self._top_unmarked(horses, marks, excluded, LONGSHOT_PLACE_VALUE, Mark.ANA, horses[LONGSHOT_PLACE_VALUE].notna())
        marks = self._top_unmarked(horses, marks, excluded, FORM_SHIFT, Mark.CHUI, horses[FORM_SHIFT] > 0)
        return horses.assign(**{MARK: marks})

    def _excluded(self, horses: pd.DataFrame) -> pd.Series:
        if np.isnan(self._exclude_line):
            return pd.Series(False, index=horses.index)
        return (horses[DANGER] >= self._exclude_line).fillna(False)

    def _top_unmarked(self, horses: pd.DataFrame, marks: pd.Series, excluded: pd.Series, column: str, mark: Mark,
                      allowed: pd.Series) -> pd.Series:
        """印の無い・消でない・``allowed`` の馬のうち、``column`` がレースでいちばん大きい馬に ``mark`` を付ける。"""
        pool = horses[marks.isna() & ~excluded & allowed]
        if pool.empty:
            return marks
        chosen = pool.groupby(RACE_ID)[column].idxmax()
        marked = marks.copy()
        marked[chosen.to_numpy()] = mark.value
        return marked
