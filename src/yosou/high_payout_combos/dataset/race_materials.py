"""馬ごとの材料から、レースごとの表を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..feature import material_names as m
from ..feature.column_names import RACE_ID
from ..feature.longshot_rule import is_backed_longshot
from ..feature.race_features import FIELD, RACE_MATERIALS
from .horse_materials import MARK_NUMBERS

#: 1番人気の単勝人気と、◎ の印の番号。
_FAVORITE_POPULARITY = 1
_TOP_MARK_NUMBER = MARK_NUMBERS["◎"]
#: 「期待度が高い」とみなす、◎ の単勝の期待値の下限。
_HIGH_EXPECTATION_VALUE = 1.0
#: 勝率の和を取る上位の頭数。
_TOP_SHARE_HORSES = 3


class RaceMaterials:
    """馬ごとの材料の表（``HorseMaterials.of``）から、レースごとの表（``race_id`` が index、列は ``RACE_MATERIALS``）を作る。

    - ``field``: 頭数（そのレースの行数）。``fav_odds``: 単勝オッズの最小。
    - ``ent``: −Σ mw × log(mw)。例: 勝率が 0.5・0.5 の2頭なら log 2 ≒ 0.69。混戦ほど大きい。
    - ``n_dg``: 危険な人気馬の数。``max_wv``: 単勝の期待値の最大。``s3``: 単勝オッズから見た勝率の大きい順に3頭の和。
    - ``n_ls``: 予想が買っている穴馬（6番人気以下で e3 が 0.05 以上）の数。
    - ``fav_dg``・``fav_e3``・``fav_rw``: 1番人気の馬の dg・e3・rw（1番人気がいなければ欠損値）。
    - ``exp_high``: ◎ の単勝の期待値が 1.0 以上なら 1、ほか（◎ が無いレースを含む）は 0。
    """

    def of(self, materials: pd.DataFrame) -> pd.DataFrame:
        by_race = materials.groupby(RACE_ID, sort=False)
        races = pd.DataFrame({
            FIELD: by_race.size().astype(float),
            "fav_odds": np.exp(by_race[m.LWO].min()),
            "ent": self._entropy(materials),
            "n_dg": by_race[m.DG].sum(),
            "max_wv": by_race[m.WV].max(),
            "s3": self._top_share(materials),
            "n_ls": self._backed_longshots(materials),
        })
        favorite = materials[materials[m.POP] == _FAVORITE_POPULARITY].groupby(RACE_ID)[[m.DG, m.E3, m.RW]].first()
        races[["fav_dg", "fav_e3", "fav_rw"]] = favorite.reindex(races.index).to_numpy()
        races["exp_high"] = self._high_expectation(materials).reindex(races.index).fillna(0.0)
        return races[list(RACE_MATERIALS)]

    def _entropy(self, materials: pd.DataFrame) -> pd.Series:
        market_win = materials[m.MW]
        return (-(market_win * np.log(market_win.clip(lower=m.FLOOR)))).groupby(materials[RACE_ID], sort=False).sum()

    def _top_share(self, materials: pd.DataFrame) -> pd.Series:
        strongest_first = materials.sort_values([RACE_ID, m.MW], ascending=[True, False], kind="stable")
        return strongest_first.groupby(RACE_ID).head(_TOP_SHARE_HORSES).groupby(RACE_ID)[m.MW].sum()

    def _backed_longshots(self, materials: pd.DataFrame) -> pd.Series:
        is_longshot = pd.Series(is_backed_longshot(materials[m.POP].to_numpy(), materials[m.E3].to_numpy()), index=materials.index)
        return is_longshot.groupby(materials[RACE_ID], sort=False).sum().astype(float)

    def _high_expectation(self, materials: pd.DataFrame) -> pd.Series:
        top_value = materials[materials[m.MK] == _TOP_MARK_NUMBER].groupby(RACE_ID)[m.WV].first()
        return (top_value >= _HIGH_EXPECTATION_VALUE).astype(float)
