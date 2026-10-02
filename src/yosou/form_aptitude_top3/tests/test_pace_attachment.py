"""展開の予想の結果（まとまり P）を足す組み立て（設計書 15 の 13）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import PACE_FORECAST_FEATURES, PredictionTiming
from yosou.shared.feature.pace_forecast import PACE_FORECAST_NAMES
from yosou.shared.feature.pace_forecast import pace_forecast_columns as names

from ..dataset import PaceAttachment
from ..feature import ABILITY_CATALOG
from ..workflow import ABILITY_TIMINGS, PACE_TIMINGS


def test_only_the_thursday_model_adds_the_pace_forecasts():
    # 7つの区切りで採用の基準を満たしたのは木曜だけ（前日・当日は満たさなかった）
    assert PACE_TIMINGS == (PredictionTiming.THURSDAY,) and set(PACE_TIMINGS) <= set(ABILITY_TIMINGS)


def test_attachment_adds_twenty_columns_and_the_catalog(ability_training_data: TrainingData):
    first = ability_training_data.ids.iloc[0]
    forecasts = pd.DataFrame({"race_id": [str(first[RACE_ID])], "horse_id": [str(first[HORSE_ID])],
                              names.LEADER: [0.4], names.CORNER4: [0.2], names.CLOSING: [0.3]})
    paced = PaceAttachment().apply(ability_training_data, forecasts)
    assert list(paced.features.columns) == [*ability_training_data.features.columns, *PACE_FORECAST_NAMES]
    assert paced.catalog.names == ABILITY_CATALOG.names + tuple(feature.name for feature in PACE_FORECAST_FEATURES)
    assert paced.features.iloc[0][names.COMBINED] == 0.5 and paced.features.iloc[1:][names.LEADER_P].isna().all()
    # 木曜の列には P が入る。2回足しても、列は増えない
    assert set(PACE_FORECAST_NAMES) <= set(paced.for_timing(PredictionTiming.THURSDAY).features.columns)
    assert PaceAttachment().apply(paced, forecasts).features.shape == paced.features.shape
