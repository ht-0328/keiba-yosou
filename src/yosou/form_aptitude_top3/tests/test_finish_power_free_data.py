"""当日の学習データにある勝ち切る材料（Q）が、1着のモデルにだけ渡ることのテスト。合成DB だけを使う。"""

from __future__ import annotations

from pathlib import Path

from 共通 import db

from yosou.shared.dataset import WIN, TrainingPeriod
from yosou.shared.feature import PredictionTiming

from ..dataset import FinishPowerFreeData, PoolFreeData, WinTargetData, race_day_dataset_builder
from ..feature import FINISH_POWER_NAMES, RACE_DAY_CATALOG, RACE_DAY_WIN_CATALOG
from .test_dataset_builder import CARD_ODDS


def test_race_day_data_carries_the_finish_power_columns_and_the_top3_side_drops_them(
        season_db: Path, season_period: TrainingPeriod, figure_cache: Path):
    with db.open_db(season_db) as con:
        builder = race_day_dataset_builder(con, figure_cache)
        data = builder.build_training_data(season_period)
        race_id = str(data.ids.iloc[0, 0])
        prediction = builder.build_prediction_data(race_id, PredictionTiming.RACE_DAY, odds=CARD_ODDS)
    assert set(FINISH_POWER_NAMES) <= set(data.features.columns) and data.catalog.names == RACE_DAY_WIN_CATALOG.names
    assert data.features[list(FINISH_POWER_NAMES)].notna().any().any()  # 過去走のある馬には値が入る
    # 3着以内のモデルに渡す形: Q を外し、一覧も当日の 285個に戻る。目的変数・基準・ID はそのまま
    top3 = FinishPowerFreeData().training(data)
    assert not set(FINISH_POWER_NAMES) & set(top3.features.columns) and top3.catalog.names == RACE_DAY_CATALOG.names
    assert top3.ids is data.ids and top3.baseline is data.baseline
    # 券種オッズなしの学習データから Q を外しても同じ
    pool_free = FinishPowerFreeData().training(PoolFreeData().training(data))
    assert not set(FINISH_POWER_NAMES) & set(pool_free.features.columns)
    # 1着のモデルに渡す形: Q を残し、目的変数は 1着
    win = WinTargetData().training(data)
    assert set(FINISH_POWER_NAMES) <= set(win.features.columns) and win.label_name == WIN
    # 予測用データも同じ
    assert set(FINISH_POWER_NAMES) <= set(prediction.features.columns)
    top3_prediction = FinishPowerFreeData().prediction(prediction)
    assert not set(FINISH_POWER_NAMES) & set(top3_prediction.features.columns) and top3_prediction.market is prediction.market
    assert set(FINISH_POWER_NAMES) <= set(WinTargetData().prediction(prediction).features.columns)
