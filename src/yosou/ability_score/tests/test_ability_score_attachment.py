"""T を学習データ・予測用データに足す・外す部品の契約。DB を使わず、手で作った表で確かめる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData
from yosou.shared.feature import BASE_FEATURES, FeatureCatalog, PredictionTiming

from ..ability_score_attachment import AbilityScoreAttachment
from ..ability_score_columns import ABILITY_INDEX, CARRIED
from ..ability_score_free_data import AbilityScoreFreeData
from ..features import ABILITY_SCORE_FEATURES, ABILITY_SCORE_NAMES, SCORE
from ..race_ability_score_attacher import RaceAbilityScoreAttacher

#: 元の特徴量の代わり（共通の一覧の最初の1つ）。
FIRST = BASE_FEATURES[0].name


def _prediction_data() -> PredictionData:
    ids = pd.DataFrame({RACE_ID: ["r1", "r1", "r2"], HORSE_ID: [11, 12, 13]}, index=[5, 6, 7])
    features = pd.DataFrame({FIRST: [1.0, 1.0, 2.0], ABILITY_INDEX: [82.0, 80.0, 79.0], CARRIED: [57.0, 55.0, 55.0]}, index=[5, 6, 7])
    return PredictionData(ids, features, PredictionTiming.DAY_BEFORE, FeatureCatalog(BASE_FEATURES[:1]))


def test_特徴量の能力指数と斤量から4列を足し_一覧にも足す():
    data = AbilityScoreAttachment().apply(_prediction_data())
    assert list(data.features.columns) == [FIRST, ABILITY_INDEX, CARRIED, *ABILITY_SCORE_NAMES] and list(data.features.index) == [5, 6, 7]
    assert data.features.loc[5, SCORE] == 81.0 and data.features.loc[7, SCORE] == 79.0
    assert data.catalog.names == (FIRST,) + ABILITY_SCORE_NAMES
    assert all(feature in data.catalog.features for feature in ABILITY_SCORE_FEATURES)
    # もう一度足しても、列も一覧も増えない（置き換える）
    again = AbilityScoreAttachment().apply(data)
    assert again.features.shape == data.features.shape and again.catalog.names == data.catalog.names


def test_外すと4列と一覧から消え_無いデータに使っても変わらない():
    data = AbilityScoreAttachment().apply(_prediction_data())
    freed = AbilityScoreFreeData().prediction(data)
    assert list(freed.features.columns) == [FIRST, ABILITY_INDEX, CARRIED] and freed.catalog.names == (FIRST,)
    assert AbilityScoreFreeData().prediction(freed).features.shape == freed.features.shape


def test_予測の流れに渡す形は_レースと時点を受け取って同じ結果を返す():
    attacher = RaceAbilityScoreAttacher()
    data = attacher.attach(_prediction_data(), "r1", PredictionTiming.DAY_BEFORE, None)
    assert list(data.features.columns)[-4:] == list(ABILITY_SCORE_NAMES)
