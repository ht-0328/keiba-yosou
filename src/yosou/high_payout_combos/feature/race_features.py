"""レースの材料（そのレースの全部の組に同じ値）。"""

from __future__ import annotations

import pandas as pd

from .column_names import RACE_ID
from .combo_members import ComboMembers
from .material_names import POP

#: レースごとの表（``RaceMaterials.of``）の列。``field`` は頭数、``fav_`` は1番人気の馬の値。
FIELD = "field"
FAVORITE_DANGER = "fav_dg"
RACE_MATERIALS: tuple[str, ...] = (
    FIELD, "fav_odds", "ent", "n_dg", "max_wv", "s3", "n_ls", FAVORITE_DANGER, "fav_e3", "fav_rw", "exp_high",
)
#: 1番人気が危険な人気馬で、組に1番人気を含まないか（1 か 0）。
FAVORITE_OUT = "fav_out_dg"
NAMES: tuple[str, ...] = (*RACE_MATERIALS, FAVORITE_OUT)
_FAVORITE_POPULARITY = 1


class RaceFeatures:
    """レースごとの表を組の行に写し、「危険な1番人気を外した組か」を足す。

    - ``field``: 頭数。``fav_odds``: 単勝オッズの最小。``ent``: 単勝オッズから見た勝率のばらつき（エントロピー）。
    - ``n_dg``: 危険な人気馬の数。``max_wv``: 単勝の期待値の最大。``s3``: 勝率の上位3頭の和。``n_ls``: 予想が買っている穴馬の数。
    - ``fav_dg``・``fav_e3``・``fav_rw``: 1番人気の馬の、危険な人気馬か・予想と複勝の市場の差・予想 ÷ 市場の比の対数。
    - ``exp_high``: ◎ の単勝の期待値が 1.0 以上か。
    - ``fav_out_dg``: 1番人気が危険な人気馬で、組のいちばん人気のある馬が2番人気以下なら 1。
    """

    def of(self, rows: pd.DataFrame, races: pd.DataFrame, members: ComboMembers) -> pd.DataFrame:
        """``rows`` は市場の表の行、``races`` は ``race_id`` を index にしたレースごとの表、``members`` はその行の組の馬の材料。"""
        mapped = races.reindex(rows[RACE_ID])[list(RACE_MATERIALS)].set_axis(rows.index)
        has_no_favorite = members.in_combo_order(POP).min(axis=1) > _FAVORITE_POPULARITY
        mapped[FAVORITE_OUT] = ((mapped[FAVORITE_DANGER].to_numpy() == 1.0) & has_no_favorite).astype(float)
        return mapped
