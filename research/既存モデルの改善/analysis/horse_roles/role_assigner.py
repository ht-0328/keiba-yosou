"""レースごとに、馬の役割（消・軸・◎）を決める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID
from yosou.shared.dataset.column_names import POPULARITY

from ..combined.horse_columns import FORM_PROBABILITY
from .role_columns import AXIS, DANGER, EXCLUDED, HONMEI, WIN_VALUE

#: 消にする人気（1番人気だけ）。
_FAVORITE = 1


class RoleAssigner:
    """1頭ごとの表（``HorseValues`` の列を持つ）に、レースごとの馬の役割を付ける。

    1. 消: 1番人気で、人気馬の危険度が ``exclude_line`` 以上（本当に危険と判定したときだけ。何でも消すわけではない）。
    2. 軸: 消を除いて、全頭の予想の3着以内の確率がいちばん高い馬（勝率も高い「安心な馬」）。2番目の馬の3着以内の確率が
       ``second_axis_line`` 以上なら、その馬も軸にして2頭軸にする。
    3. ◎: 消を除いて、単勝の期待値がいちばん高い馬（勝ってほしい馬）。軸と同じ馬でもよい。

    例: 1番人気が消なら、残りの馬の中で軸と◎を決める。
    """

    def __init__(self, exclude_line: float, second_axis_line: float) -> None:
        self._exclude_line = exclude_line
        self._second_axis_line = second_axis_line

    def assign(self, horses: pd.DataFrame) -> pd.DataFrame:
        excluded = ((horses[POPULARITY] == _FAVORITE) & (horses[DANGER] >= self._exclude_line)).fillna(False)
        remaining = horses[~excluded]
        rank = remaining.groupby(RACE_ID)[FORM_PROBABILITY].rank(method="first", ascending=False)
        is_second = (rank == 2) & (remaining[FORM_PROBABILITY] >= self._second_axis_line)
        axis = pd.Series(0, index=horses.index)
        axis[rank.index[rank == 1]] = 1
        axis[is_second.index[is_second]] = 2
        honmei = pd.Series(False, index=horses.index)
        honmei[remaining.groupby(RACE_ID)[WIN_VALUE].idxmax().dropna().to_numpy()] = True
        return horses.assign(**{EXCLUDED: excluded.to_numpy(), AXIS: axis.to_numpy(), HONMEI: honmei.to_numpy()})
