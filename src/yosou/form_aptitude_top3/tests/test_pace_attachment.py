"""展開の予想の結果（まとまり P）を足す組み立て（設計書 15 の 13）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import PACE_FORECAST_FEATURES, PredictionTiming
from yosou.shared.feature.pace_forecast import PACE_FORECAST_NAMES
from yosou.shared.feature.pace_forecast import pace_forecast_columns as names

from ..dataset import PaceAttachment
from ..feature import ABILITY_CATALOG
from ..workflow import (
    ABILITY_SCORE_TIMINGS,
    ABILITY_SCORE_TOP3_TIMINGS,
    ABILITY_SCORE_WIN_TIMINGS,
    ABILITY_TIMINGS,
    PACE_TIMINGS,
    SCORE_TIMINGS,
    SCORE_TOP3_TIMINGS,
    SCORE_WIN_TIMINGS,
    TRACK_BIAS_TIMINGS,
    TRACK_BIAS_TOP3_TIMINGS,
    TRACK_BIAS_WIN_TIMINGS,
    WEIGHT_DISCOUNT_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_WIN_TIMINGS,
)


def test_only_the_thursday_model_adds_the_pace_forecasts():
    # 7つの区切りで採用の基準を満たしたのは木曜だけ（前日・当日は満たさなかった）
    assert PACE_TIMINGS == (PredictionTiming.THURSDAY,) and set(PACE_TIMINGS) <= set(ABILITY_TIMINGS)
    # 展開スコア（S）は、3着以内のモデルは前日だけ（設計書 15 の 17）。学習データに足す時点は、どちらかのモデルが使う時点
    assert SCORE_TOP3_TIMINGS == (PredictionTiming.DAY_BEFORE,) and SCORE_WIN_TIMINGS == ()
    assert set(SCORE_TIMINGS) == set(SCORE_TOP3_TIMINGS) | set(SCORE_WIN_TIMINGS)
    # 能力スコア（T）は、木曜の3着以内と1着に足す（設計書 15 の 18。前日・当日は印の成績か誤差の基準で見送り）
    assert ABILITY_SCORE_TOP3_TIMINGS == (PredictionTiming.THURSDAY,) and ABILITY_SCORE_WIN_TIMINGS == (PredictionTiming.THURSDAY,)
    assert set(ABILITY_SCORE_TIMINGS) == set(ABILITY_SCORE_TOP3_TIMINGS) | set(ABILITY_SCORE_WIN_TIMINGS)
    # トラックバイアスの補正（U）も同じ形（設計書 15 の 19）。馬番が要るので木曜には足せない
    assert set(TRACK_BIAS_TIMINGS) == set(TRACK_BIAS_TOP3_TIMINGS) | set(TRACK_BIAS_WIN_TIMINGS)
    assert PredictionTiming.THURSDAY not in TRACK_BIAS_TIMINGS
    # 馬体重の表の割引（V）も同じ形（設計書 15 の 20）。馬体重の発表は当日なので当日にしか足せない
    assert set(WEIGHT_DISCOUNT_TIMINGS) == set(WEIGHT_DISCOUNT_TOP3_TIMINGS) | set(WEIGHT_DISCOUNT_WIN_TIMINGS)
    assert set(WEIGHT_DISCOUNT_TIMINGS) <= {PredictionTiming.RACE_DAY}


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
