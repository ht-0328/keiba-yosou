"""S を学習データ・予測用データに足す部品の契約。DB を使わず、手で作った表で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData
from yosou.shared.feature import BASE_FEATURES, FeatureCatalog, PredictionTiming

from .. import names
from ..features import DEVELOPMENT_SCORE_FEATURES, DEVELOPMENT_SCORE_NAMES
from ..score_attachment import ScoreAttachment


#: 元の特徴量の代わり（共通の一覧の最初の1つ）。
FIRST = BASE_FEATURES[0].name


def _prediction_data() -> PredictionData:
    ids = pd.DataFrame({RACE_ID: ["r1", "r1", "r2"], HORSE_ID: [11, 12, 13]}, index=[5, 6, 7])
    features = pd.DataFrame({FIRST: [1.0, 1.0, 2.0]}, index=[5, 6, 7])
    return PredictionData(ids, features, PredictionTiming.DAY_BEFORE, FeatureCatalog(BASE_FEATURES[:1]))


def test_同じ出走に展開スコアの5列を足し_一覧にも足す():
    scored = pd.DataFrame({"race_id": ["r1", "r1"], "horse_id": ["11", "12"], names.SCORE: [0.012, -0.004],
                           **{name: [0.003, -0.001] for name in names.CONTRIBUTIONS}})
    data = ScoreAttachment().apply(_prediction_data(), scored)
    assert list(data.features.columns) == [FIRST, *DEVELOPMENT_SCORE_NAMES] and list(data.features.index) == [5, 6, 7]
    assert data.features.loc[5, names.SCORE] == 0.012 and np.isnan(data.features.loc[7, names.SCORE])   # 表に無い出走は欠損値
    assert data.catalog.names == (FIRST,) + DEVELOPMENT_SCORE_NAMES
    assert all(feature in data.catalog.features for feature in DEVELOPMENT_SCORE_FEATURES)
    # もう一度足しても、列も一覧も増えない（置き換える）
    again = ScoreAttachment().apply(data, scored.assign(**{names.SCORE: [0.5, 0.5]}))
    assert again.features.shape == data.features.shape and again.features.loc[5, names.SCORE] == 0.5
    assert again.catalog.names == data.catalog.names
