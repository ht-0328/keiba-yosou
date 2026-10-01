"""全頭で特徴量を作り、最後に人気範囲で絞る。元DBの取得処理は共通部品を使う。"""

import pandas as pd

from yosou.shared.dataset import (
    FlatRunnerFilter, HistoryRecordsLoader, PredictionData, RaceRecordsLoader, TrainingData,
)
from yosou.shared.feature.value_types import as_numbers
from yosou.shared.repository import TargetScope

from ..extra_data import ExtraDataLoader, RaceRelation
from ..feature.builder import SelectedFeatureBuilder
from ..feature.registry import FeatureRegistry
from ..setting import ModelSettings
from .announcement_check import AnnouncementCheck
from .dataset_columns import IDS, MARKET, MARKET_FIELD_SIZE, MARKET_WHOLE_FIELD, USED_POPULARITY
from .odds_baseline import OddsBaseline
from .popularity_filter import PopularityFilter
from .training_data_selector import TrainingDataSelector


class CustomDataset:
    """学習データ・予測用データを作る。全頭で特徴量を作ってから、人気範囲と条件で絞る。"""

    def __init__(self, con, settings: ModelSettings, registry: FeatureRegistry) -> None:
        self.settings = settings
        self.builder = SelectedFeatureBuilder(registry, settings.selected, settings.timing, settings.conditions.names)
        self.history = HistoryRecordsLoader(con)
        self.races = RaceRecordsLoader(con)
        self.extra = ExtraDataLoader(con)

    def training(self) -> TrainingData:
        records = self.history.load(self.settings.period.warmup_first_day)
        rows = FlatRunnerFilter().apply(records.entries)
        rows = rows[rows["race_date"] >= pd.Timestamp(self.settings.period.train_first_day)]
        # 確定成績を読むが、正常出走で着順不明の行は負例にしない。
        resolved = as_numbers(rows["finish"]).ge(1) | rows["abnormal"].isin(["4", "5"])
        rows = rows[resolved]
        if rows.empty:
            raise ValueError("学習に使える確定成績がありません")
        rows = self.extra.attach(rows, TargetScope.since(self.settings.period.train_first_day).relation, self.builder.sources)
        frame = self.builder.build(records.with_entries(rows))
        return TrainingDataSelector().select(rows, frame, self.settings, self.builder.catalog)

    def prediction(self, race_id: str, popularity=None, odds=None) -> PredictionData:
        records = self.races.load(race_id, popularity, odds)
        if (records.entries["surface"] == "障害").any():
            raise ValueError("障害レースはこのモデルの対象外です")
        rows = FlatRunnerFilter().apply(records.entries)
        rows = self.extra.attach(rows, RaceRelation().of(race_id), self.builder.sources)
        kept = rows[PopularityFilter().mask(rows, self.settings.popularity)]
        if kept.empty:
            return self._empty_data(rows, kept)
        AnnouncementCheck(self.builder, self.settings.odds_baseline).check(rows)
        frame = self.builder.build(records.with_entries(rows))
        kept = kept[self.settings.conditions.mask(frame.loc[kept.index])]
        if kept.empty:
            return self._empty_data(rows, kept)
        features = frame.loc[kept.index, list(self.settings.selected)]
        baseline = OddsBaseline(self.settings.target).build(rows).at(kept.index) if self.settings.odds_baseline else None
        return self._prediction_data(rows, kept, features, baseline)

    def _empty_data(self, rows: pd.DataFrame, kept: pd.DataFrame) -> PredictionData:
        """対象の馬がいない（人気範囲・条件に当てはまらない）ときの、0行の予測用データ。"""
        features = pd.DataFrame(index=kept.index, columns=list(self.settings.selected))
        return self._prediction_data(rows, kept, features, None)

    def _prediction_data(self, rows: pd.DataFrame, kept: pd.DataFrame, features: pd.DataFrame,
                         baseline) -> PredictionData:
        ids = IDS.select(kept).assign(**{USED_POPULARITY: kept["popularity"]})
        # 3着以内の確率を頭数にそろえ直せるのは、同じレースの全頭が対象のときだけ。
        market = MARKET.select(kept).assign(**{MARKET_FIELD_SIZE: len(rows), MARKET_WHOLE_FIELD: len(kept) == len(rows)})
        return PredictionData(ids, features, self.settings.timing, self.builder.catalog, baseline, market)
