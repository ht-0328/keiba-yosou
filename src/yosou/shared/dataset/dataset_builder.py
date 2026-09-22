"""学習データと予測用データを作る入口。"""

from __future__ import annotations

from collections.abc import Mapping

from ..feature import EntryColumns, FeatureBuilder, PredictionTiming
from . import column_names as names
from .history_records_loader import HistoryRecordsLoader
from .prediction_data import PredictionData
from .race_records_loader import RaceRecordsLoader
from .required_info_check import RequiredInfoCheck
from .sample_selector import SampleSelector
from .target_labeler import TargetLabeler
from .training_data import TrainingData
from .training_period import TrainingPeriod

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

    どちらも同じ手順（記録を集める → 行を選ぶ → 特徴量を作る → 残す行を決める）を通し、学習と予測で
    特徴量の中身がずれないようにする（設計書 11 の 4）。予想ごとに違うところ（入れる行・目的変数・特徴量の一覧）は、
    作られるときに受け取る ``selector``・``target_builder``・``feature_builder`` の中にある。
    """

    def __init__(self, history_loader: HistoryRecordsLoader, race_loader: RaceRecordsLoader,
                 selector: SampleSelector, target_builder: TargetLabeler,
                 feature_builder: FeatureBuilder) -> None:
        self._history_loader = history_loader
        self._race_loader = race_loader
        self._selector = selector
        self._target_builder = target_builder
        self._feature_builder = feature_builder
        self._required_info = RequiredInfoCheck()

    def build_training_data(self, period: TrainingPeriod) -> TrainingData:
        """``period`` の学習データの始まりからの出走で、学習データを作る。特徴量は当日の時点の全部。

        ウォームアップの始まりからの出走を読み、学習データの始まりより前の行は過去走の計算にだけ使う。
        """
        records = self._history_loader.load(period.warmup_first_day)
        samples = self._selector.training_samples(records.entries, period.train_first_day)
        sample_records = records.with_entries(samples)
        features = self._feature_builder.build(sample_records, PredictionTiming.RACE_DAY)
        kept = self._selector.keep_samples(samples)
        return TrainingData(
            ids=_ID_COLUMNS.select(kept),
            features=features.loc[kept.index],
            targets=self._target_builder.build(kept),
            evaluation=_EVALUATION_COLUMNS.select(kept),
            catalog=self._feature_builder.catalog,
            label_name=self._target_builder.label_name,
        )

    def build_prediction_data(self, race_id: str, timing: PredictionTiming,
                              popularity: Mapping[int, int] | None = None) -> PredictionData:
        """1レースの出走馬の予測用データを作る。特徴量は ``timing`` の時点で使うものだけ。

        ``popularity`` は 馬番 → 単勝人気。まだ DB に無い人気を、利用者が手で渡すときに使う。
        障害レースと、その時点で要る情報（馬番・馬場状態・馬体重）がまだ DB に無いときは ``ValueError``。
        """
        records = self._race_loader.load(race_id, popularity)
        runners = self._selector.prediction_runners(records.entries, race_id)
        features = self._feature_builder.build(records.with_entries(runners), timing)
        kept = self._selector.keep_samples(runners)
        kept_features = features.loc[kept.index]
        self._required_info.check(kept_features)
        return PredictionData(
            ids=_ID_COLUMNS.select(kept), features=kept_features, timing=timing,
            catalog=self._feature_builder.catalog,
        )
