"""元DB から、この予想の学習データを読む。"""

from __future__ import annotations

from datetime import date

import duckdb

from yosou.shared.dataset import TrainingData, TrainingPeriod

from ..dataset import dataset_builder
from ..setting import BuyOrFadeSettings

#: 検証データ・テストデータの区切り。この予想は時期で学習と評価を分ける（``YearlyEvaluation``）ので、
#: 共通の ``TrainingPeriod`` の区切りは使わない。どの開催日よりも後の日にしておく。
_UNUSED_VALID_FIRST_DAY = date(9998, 1, 1)
_UNUSED_TEST_FIRST_DAY = date(9999, 1, 1)


class TrainingDataReader:
    """方針の「学習の最初の年」の1月1日から、元DB にある最後の開催日までの1番人気の学習データを読む。

    その前の年はウォームアップ（過去走の特徴量の計算にだけ使う）。特徴量は当日の時点の全部で、
    時点ごとの列は ``TrainingData.for_timing`` で選ぶ。
    """

    def __init__(self, settings: BuyOrFadeSettings) -> None:
        self._settings = settings

    def read(self, con: duckdb.DuckDBPyConnection) -> TrainingData:
        period = TrainingPeriod.starting(
            date(self._settings.train_first_year, 1, 1), _UNUSED_VALID_FIRST_DAY, _UNUSED_TEST_FIRST_DAY,
        )
        return dataset_builder(con).build_training_data(period)
