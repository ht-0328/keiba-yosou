"""全頭の予想①の学習データ（当日の馬場傾向 U つき）を作って pickle にとっておく。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import db

from yosou.local_form_aptitude_top3.dataset import local_dataset_builder
from yosou.local_track_bias import LOCAL_TRACK_BIAS_FEATURES, LocalBiasHistory
from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.track_bias import BiasAttachment, BiasRunRepository


class LocalTrainingDataCache:
    """①の ``train`` と同じ作り方（``local_dataset_builder`` ＋ 当日の馬場傾向 U）で学習データを作り、``folder`` に pickle で書く。
    同じ期間のファイルがあれば読むだけ（作るのに 20〜30分かかるため）。元DB は作るときだけ開く。"""

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def path(self, period: TrainingPeriod) -> Path:
        return self._folder / f"全頭の学習データ-{period.train_first_day.isoformat()}-{period.test_first_day.isoformat()}.pkl"

    def load_or_build(self, db_path: Path | None, period: TrainingPeriod) -> TrainingData:
        path = self.path(period)
        if path.exists():
            return pd.read_pickle(path)
        with db.open_db(db_path, default=db.LOCAL) as con:
            data = local_dataset_builder(con).build_training_data(period)
            runs = BiasRunRepository(con).read(period.warmup_first_day)
        data = BiasAttachment(LOCAL_TRACK_BIAS_FEATURES).apply(data, LocalBiasHistory().of(PredictionTiming.RACE_DAY, runs))
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle(data, path)
        return data
