"""学習データと予測用データを作る入口。"""

from __future__ import annotations

from datetime import date

import duckdb

from ..feature import EntryColumns, FeatureBuilder, PredictionTiming
from . import column_names as names
from .history_records_loader import HistoryRecordsLoader
from .prediction_data import PredictionData
from .race_records_loader import RaceRecordsLoader
from .required_info_check import RequiredInfoCheck
from .runner_selector import RunnerSelector
from .target_builder import TargetBuilder
from .training_data import TrainingData

#: 過去走の特徴量を計算するために読む最初の開催日（ウォームアップ期間の始まり。DB にある中央の成績の始まり）。
HISTORY_FIRST_DAY = date(2023, 1, 1)

#: ID 列（学習データの列名 → 出走の記録の列名）。
_ID_COLUMNS = EntryColumns({
    names.RACE_ID: "race_id", names.RACE_DATE: "race_date", names.HORSE_ID: "horse_id",
    names.HORSE_NO: "horse_no", names.HORSE_NAME: "horse_name",
})
#: 評価用の列（学習データの列名 → 出走の記録の列名）。
_EVALUATION_COLUMNS = EntryColumns({
    names.FINISH: "finish", names.WIN_ODDS: "win_odds", names.POPULARITY: "popularity",
    names.WIN_PAYOUT: "win_payout", names.PLACE_PAYOUT: "place_payout",
})


class DatasetBuilder:
    """学習データと予測用データを作る。

    どちらも同じ手順（記録を集める → 行を選ぶ → 特徴量を作る）を通し、学習と予測で特徴量の中身が
    ずれないようにする（設計書 11 の 4）。
    """

    def __init__(self, history_loader: HistoryRecordsLoader, race_loader: RaceRecordsLoader) -> None:
        self._history_loader = history_loader
        self._race_loader = race_loader
        self._selector = RunnerSelector()
        self._feature_builder = FeatureBuilder()
        self._target_builder = TargetBuilder()
        self._required_info = RequiredInfoCheck()

    @classmethod
    def for_database(cls, con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
        """元DB への接続から作る。"""
        return cls(HistoryRecordsLoader(con), RaceRecordsLoader(con))

    def build_training_data(self) -> TrainingData:
        """2024年1月からの中央の芝・ダートの出走で、学習データを作る。特徴量は当日の時点の 68個。"""
        records = self._history_loader.load(HISTORY_FIRST_DAY)
        samples = self._selector.training_samples(records.entries)
        sample_records = records.with_entries(samples)
        return TrainingData(
            ids=_ID_COLUMNS.select(samples),
            features=self._feature_builder.build(sample_records, PredictionTiming.RACE_DAY),
            targets=self._target_builder.build(samples),
            evaluation=_EVALUATION_COLUMNS.select(samples),
        )

    def build_prediction_data(self, race_id: str, timing: PredictionTiming) -> PredictionData:
        """1レースの出走馬の予測用データを作る。特徴量は ``timing`` の時点で使うものだけ。

        障害レースと、その時点で要る情報（馬番・馬場状態・馬体重）がまだ DB に無いときは ``ValueError``。
        """
        records = self._race_loader.load(race_id)
        runners = self._selector.prediction_runners(records.entries, race_id)
        features = self._feature_builder.build(records.with_entries(runners), timing)
        self._required_info.check(features)
        return PredictionData(ids=_ID_COLUMNS.select(runners), features=features, timing=timing)
