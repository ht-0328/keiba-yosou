"""人気馬の予想の学習データに、サインの列とレースのグレードを足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import FeatureCatalog

from .sign_features import SIGN_FEATURES

#: 評価用の列に足す、レースのグレードコード（平地の G1 = A・G2 = B・G3 = C。重賞でなければ空）。
GRADE = "グレード"


class SignTrainingTable:
    """人気馬の予想の学習データ（``base``）の行に、サインの表（``SignTableBuilder``）の同じ出走の値を突き合わせて足す。

    特徴量にサインの30列（``SIGN_FEATURES``）を、評価用の列にグレード（``GRADE``）を足す。行の並びと数は変えない。
    サインの表に無い出走（無いはずだが）は、特徴量が NaN、グレードが空になる。
    """

    def attach(self, base: TrainingData, signs: pd.DataFrame) -> TrainingData:
        names = [feature.name for feature in SIGN_FEATURES]
        keyed = signs.rename(columns={"race_id": RACE_ID, "horse_id": HORSE_ID})
        keyed = keyed.assign(**{RACE_ID: keyed[RACE_ID].astype(str), HORSE_ID: keyed[HORSE_ID].astype(str)})
        keys = base.ids[[RACE_ID, HORSE_ID]].astype(str).reset_index(drop=True)
        matched = keys.merge(keyed[[RACE_ID, HORSE_ID, "grade_code", *names]], on=[RACE_ID, HORSE_ID], how="left")
        if len(matched) != len(keys):
            raise ValueError("サインの表に、同じ出走の行が2つ以上あります")
        matched.index = base.ids.index
        features = pd.concat([base.features, matched[names].astype(float)], axis=1)
        evaluation = base.evaluation.assign(**{GRADE: matched["grade_code"].fillna("")})
        catalog = FeatureCatalog(base.catalog.features + SIGN_FEATURES)
        return replace(base, features=features, evaluation=evaluation, catalog=catalog)
