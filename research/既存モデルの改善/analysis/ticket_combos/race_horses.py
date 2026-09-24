"""1レースの、買い目を作るのに使う馬の並び。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.dataset import HORSE_NO

from ..horse_roles.role_columns import AXIS, EXCLUDED, HONMEI, POPULAR


@dataclass(frozen=True)
class RaceHorses:
    """1レースの馬番の並び（消の馬は、どれにも入らない）。

    - ``runners``: 消でない全部の馬。``popular``・``holes``: そのうちの人気と穴。
    - ``axes``: 軸（1頭か2頭。1頭目が先）。``honmei``: ◎（いなければ None）。
    """

    runners: tuple[int, ...]
    popular: tuple[int, ...]
    holes: tuple[int, ...]
    axes: tuple[int, ...]
    honmei: int | None

    @classmethod
    def of(cls, group: pd.DataFrame) -> RaceHorses:
        kept = group[~group[EXCLUDED].astype(bool)]
        numbers = kept[HORSE_NO].astype(int)
        axes = kept[kept[AXIS] > 0].sort_values(AXIS)[HORSE_NO].astype(int)
        honmei = kept.loc[kept[HONMEI].astype(bool), HORSE_NO].astype(int)
        return cls(tuple(numbers), tuple(numbers[kept[POPULAR].astype(bool)]), tuple(numbers[~kept[POPULAR].astype(bool)]),
                   tuple(axes), int(honmei.iloc[0]) if len(honmei) else None)
