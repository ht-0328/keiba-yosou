"""S を外す部品の契約。DB を使わず、手で作った表で確かめる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData
from yosou.shared.feature import BASE_FEATURES, FeatureCatalog, PredictionTiming

from .. import names
from ..features import DEVELOPMENT_SCORE_NAMES
from ..score_attachment import ScoreAttachment
from ..score_free_data import DevelopmentScoreFreeData

FIRST = BASE_FEATURES[0].name


def test_展開スコアの5列と一覧の5個を外す_無ければ何も変わらない():
    ids = pd.DataFrame({RACE_ID: ["r1", "r1"], HORSE_ID: [11, 12]})
    plain = PredictionData(ids, pd.DataFrame({FIRST: [1.0, 2.0]}), PredictionTiming.DAY_BEFORE, FeatureCatalog(BASE_FEATURES[:1]))
    scored = pd.DataFrame({"race_id": ["r1"], "horse_id": ["11"], names.SCORE: [0.01], **{name: [0.0] for name in names.CONTRIBUTIONS}})
    with_score = ScoreAttachment().apply(plain, scored)
    freed = DevelopmentScoreFreeData().prediction(with_score)
    assert list(freed.features.columns) == [FIRST] and freed.catalog.names == (FIRST,)
    assert not set(DEVELOPMENT_SCORE_NAMES) & set(freed.features.columns)
    same = DevelopmentScoreFreeData().prediction(plain)
    assert list(same.features.columns) == [FIRST] and same.catalog.names == plain.catalog.names
