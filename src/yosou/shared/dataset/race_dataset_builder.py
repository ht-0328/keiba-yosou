"""レース単位の学習データと予測用データを作る入口。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import timedelta

import pandas as pd

from ..feature import PEOPLE_WINDOW_DAYS, EntryColumns, PredictionTiming, RaceFeatureBuilder
from ..repository import RacePayoutRepository
from . import column_names as names
from .field_odds_check import FieldOddsCheck
from .history_records_loader import HistoryRecordsLoader
from .prediction_data import PredictionData
from .race_records_loader import RaceRecordsLoader
from .race_result_summary import RaceResultSummary
from .race_target_labeler import RaceTargetLabeler
from .required_info_check import RequiredInfoCheck
from .sample_selector import SampleSelector
from .training_data import TrainingData
from .training_period import TrainingPeriod

#: ID 列（学習データの列名 → 出走の記録の列名）。レース単位なので、馬の列は無い。
_ID_COLUMNS = EntryColumns({
    names.RACE_ID: "race_id", names.RACE_DATE: "race_date", names.VENUE: "venue", names.RACE_NO: "race_no",
})


class RaceDatasetBuilder:
    """1行 = 1レースの学習データと予測用データを作る（荒れ具合の設計書 04 の 1・05 の図1・図2）。

    1頭ごとの ``DatasetBuilder`` の隣に置く。手順は「1頭ごとの記録を集める → 行（1頭）を選ぶ → 払戻を読む →
    1頭ごとの特徴量を作ってレース単位に集約する → レースの結果を読む → 目的変数を付ける」で、
    学習と予測で同じ ``RaceFeatureBuilder`` を使う（設計書 11 の 4）。既存の ``DatasetBuilder``・``FeatureBuilder`` は触らない。

    - ``selector``: 入れる行（1頭）の選び方。レース単位の予想は、全頭を残す。
    - ``target_labeler``: レースごとの払戻から目的変数（複数列でよい）を付ける。
    - ``payout_columns``: 評価用の列に残す払戻の列（学習データの列名 → 払戻の表の列名）。
    - ``class_labels``: 目的変数の値の並び（荒れ具合なら 0〜3）。
    - ``required_info``: その時点で要る情報（馬場状態・1番人気のオッズ など）の確認。
    """

    def __init__(self, history_loader: HistoryRecordsLoader, race_loader: RaceRecordsLoader,
                 payout_repository: RacePayoutRepository, selector: SampleSelector,
                 target_labeler: RaceTargetLabeler, feature_builder: RaceFeatureBuilder,
                 payout_columns: Mapping[str, str], class_labels: Sequence[int],
                 required_info: RequiredInfoCheck) -> None:
        self._history_loader = history_loader
        self._race_loader = race_loader
        self._payout_repository = payout_repository
        self._selector = selector
        self._target_labeler = target_labeler
        self._feature_builder = feature_builder
        self._payout_columns = EntryColumns(payout_columns)
        self._class_labels = tuple(class_labels)
        self._required_info = required_info
        self._result_summary = RaceResultSummary()
        self._field_odds_check = FieldOddsCheck()

    def build_training_data(self, period: TrainingPeriod) -> TrainingData:
        """``period`` の学習データの始まりからのレースで、学習データを作る。特徴量は当日の時点の全部。

        ウォームアップの始まりからの出走と払戻を読み、学習データの始まりより前のレースは、近走と過去の荒れ率の
        計算にだけ使う。
        """
        records = self._history_loader.load(period.warmup_first_day)
        samples = self._selector.training_samples(records.entries, period.train_first_day)
        payouts = self._payout_repository.read(period.warmup_first_day)
        features = self._feature_builder.build(records.with_entries(samples), payouts, PredictionTiming.RACE_DAY)
        race_ids = features.index
        by_race = payouts.set_index("race_id").reindex(race_ids)
        evaluation = pd.concat([
            self._result_summary.build(samples).reindex(race_ids), self._payout_columns.select(by_race),
        ], axis=1)
        return TrainingData(
            ids=self._ids(samples, race_ids),
            features=features.reset_index(drop=True),
            targets=self._target_labeler.build(by_race).reset_index(drop=True),
            evaluation=evaluation.reset_index(drop=True),
            catalog=self._feature_builder.catalog,
            label_name=self._target_labeler.label_names[0],
            class_labels=self._class_labels,
        )

    def build_prediction_data(self, race_id: str, timing: PredictionTiming,
                              odds: Mapping[int, float] | None = None) -> PredictionData:
        """1レースの予測用データ（1行）を作る。特徴量は ``timing`` の時点で使うものだけ。

        ``odds`` は 馬番 → 単勝オッズ（利用者が渡したものか、締め切り前のもの）。
        障害レース、前日以降で一部の馬にオッズが無いとき、その時点で要る情報がまだ DB に無いときは ``ValueError``。
        """
        records = self._race_loader.load(race_id, odds=odds)
        runners = self._selector.prediction_runners(records.entries, race_id)
        self._field_odds_check.check(runners, timing)
        payouts = self._payout_repository.read(self._history_first_day(runners))
        features = self._feature_builder.build(records.with_entries(runners), payouts, timing)
        self._required_info.check(features)
        return PredictionData(
            ids=self._ids(runners, features.index), features=features.reset_index(drop=True),
            timing=timing, catalog=self._feature_builder.catalog,
        )

    def _history_first_day(self, runners: pd.DataFrame):
        """過去の荒れ率のために読む払戻の最初の日（開催日の前日までの 365日が入るように）。"""
        race_day = pd.Timestamp(runners["race_date"].iloc[0]).date()
        return race_day - timedelta(days=PEOPLE_WINDOW_DAYS + 1)

    def _ids(self, runners: pd.DataFrame, race_ids: pd.Index) -> pd.DataFrame:
        """レースごとの ID 列（``race_ids`` の順）。"""
        race_rows = runners.drop_duplicates("race_id").set_index("race_id", drop=False).loc[race_ids]
        return _ID_COLUMNS.select(race_rows).reset_index(drop=True)
