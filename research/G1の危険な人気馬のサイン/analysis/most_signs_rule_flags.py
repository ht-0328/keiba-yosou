"""各レースで、サインにいちばん多く当てはまる人気馬1頭を消にする決まり（学習しない）の、消の表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData

from .sign_columns import SIGN_COUNT

#: 決まりの名前（印の成績の置き場所のフォルダ名にもなる）と、表に出す名前。
MOST_RULE_KEY = "rule-most_signs"
MOST_RULE_NAME = "サインにいちばん多く当てはまる1頭を消（学習しない）"
#: 確定の単勝人気の列（評価用の列）。
_POPULARITY = "確定の単勝人気"


class MostSignsRuleFlags:
    """サインを足した学習データ（人気馬だけの行）から、レースごとにサインの数がいちばん多い人気馬1頭を消にする表を作る。

    サインの数が同じ馬が複数いれば、人気の高い馬（1番人気が先）を消にする（今の消の「1番人気を優先」に合わせる）。
    どの人気馬もサインに当てはまらないレースでは、消を付けない。列は道具「印の成績」の ``--danger-flags`` が読む形。
    """

    def build(self, data: TrainingData) -> pd.DataFrame:
        table = pd.DataFrame({
            "race_id": data.ids[RACE_ID].astype(str).to_numpy(), "horse_id": data.ids[HORSE_ID].astype(str).to_numpy(),
            "favorite_band": data.evaluation[FAVORITE_BAND].to_numpy(),
            "signs": data.features[SIGN_COUNT].to_numpy(), "popularity": data.evaluation[_POPULARITY].to_numpy(),
        })
        ordered = table.sort_values(["race_id", "signs", "popularity"], ascending=[True, False, True])
        first = ordered.groupby("race_id").head(1)
        chosen = first.index[first["signs"].ge(1)]
        table["is_danger"] = table.index.isin(chosen)
        return table[["race_id", "horse_id", "favorite_band", "is_danger"]]
