"""出走ごとのサインの表（材料・サイン・数）を作る。"""

from __future__ import annotations

import pandas as pd

from .danger_signs import DangerSigns
from .gate_bias_features import GateBiasFeatures
from .horse_history_features import HorseHistoryFeatures
from .sign_columns import FILLY_AGAINST_COLTS, MATERIAL_COLUMNS, SIGN_COLUMNS, SIGN_COUNT, TOP_FAVORITE_ODDS

#: サインの表の鍵と、鍵のほかに残す出走の列（成績を数えるのに使う。モデルには渡さない）。
KEY_COLUMNS: tuple[str, ...] = ("race_id", "horse_id")
RUN_COLUMNS_KEPT: tuple[str, ...] = (
    "race_date", "grade_code", "stakes_no", "surface", "field_size", "popularity", "win_odds", "finish",
    "win_payout", "place_payout",
)
#: 3歳牝馬の混合戦とみなす馬齢と性別。
_THREE_YEARS_OLD = 3
_FILLY = "牝"


class SignTableBuilder:
    """全出走（``RunHistoryRepository``）から、1行 = 1頭の出走のサインの表を作る。

    列は 鍵（race_id・horse_id）・出走の列（``RUN_COLUMNS_KEPT``）・材料（``MATERIAL_COLUMNS``）・サイン（``SIGN_COLUMNS``）・
    サインの数。どの材料も、その出走より前の走と、前日までに分かる値（馬番・人気・オッズ）だけで作る。
    人気とオッズは確定の値（今の予想の学習と同じ扱い）。
    """

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        runs = runs.reset_index(drop=True)
        frame = pd.concat([runs, HorseHistoryFeatures().compute(runs), GateBiasFeatures().compute(runs)], axis=1)
        frame[FILLY_AGAINST_COLTS] = (runs["age"].eq(_THREE_YEARS_OLD) & runs["sex"].eq(_FILLY)
                                      & runs["mixed_sex"].fillna(False).astype(bool)).astype(int)
        frame[TOP_FAVORITE_ODDS] = runs.groupby("race_id")["win_odds"].transform("min")
        signs = DangerSigns().compute(frame)
        table = pd.concat([frame[[*KEY_COLUMNS, *RUN_COLUMNS_KEPT, *MATERIAL_COLUMNS]], signs], axis=1)
        return table[[*KEY_COLUMNS, *RUN_COLUMNS_KEPT, *MATERIAL_COLUMNS, *SIGN_COLUMNS, SIGN_COUNT]]
