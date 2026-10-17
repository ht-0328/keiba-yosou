"""サインに当てはまった人気馬を消にする決まり（学習しない）の、消の表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData

from .sign_columns import SIGN_COUNT

#: 決まりの名前（印の成績の置き場所のフォルダ名にもなる）と、表に出す名前。
RULE_KEY = "rule-any_sign"
RULE_NAME = "サインに1つでも当てはまったら消（学習しない）"
#: 消にするサインの数の下限。
_MIN_SIGNS = 1


class SignRuleFlags:
    """サインを足した学習データ（人気馬だけの行）から、サインに1つでも当てはまった人気馬を消にする表を作る。

    列は道具「印の成績」の ``--danger-flags`` が読む形（race_id・horse_id・favorite_band・is_danger）。
    1レースに当てはまる馬が何頭いても、全部消にする（1番人気を優先する・1レース1頭の決まりは当てない）。
    """

    def build(self, data: TrainingData) -> pd.DataFrame:
        return pd.DataFrame({
            "race_id": data.ids[RACE_ID].astype(str).to_numpy(), "horse_id": data.ids[HORSE_ID].astype(str).to_numpy(),
            "favorite_band": data.evaluation[FAVORITE_BAND].to_numpy(),
            "is_danger": data.features[SIGN_COUNT].ge(_MIN_SIGNS).to_numpy(),
        })
