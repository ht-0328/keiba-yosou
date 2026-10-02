"""全頭・全特徴量の表。元DB から1回だけ作り、pickle に保存して何度も使う。"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from yosou.custom_binary.extra_data import ExtraDataLoader
from yosou.custom_binary.feature.builder import SelectedFeatureBuilder
from yosou.custom_binary.feature.registry import FeatureRegistry
from yosou.shared.dataset import FlatRunnerFilter, HistoryRecordsLoader
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.value_types import as_numbers
from yosou.shared.repository import TargetScope

from .search_periods import SearchPeriods

#: 出走の行から残す列。行を絞る・正解を作る・回収率を計算するのに使う（モデルには渡さない）。
ROW_COLUMNS = (
    "race_id", "race_date", "horse_id", "horse_no", "horse_name", "finish", "popularity", "win_odds",
    "win_payout", "place_payout", "place_odds_low", "abnormal", "surface", "field_size",
)


@dataclass(frozen=True)
class FeatureTable:
    """``rows`` は出走の行（``ROW_COLUMNS``）、``frame`` は同じ行の全特徴量（当日の時点）。"""

    rows: pd.DataFrame
    frame: pd.DataFrame

    @classmethod
    def build(cls, con, registry: FeatureRegistry, periods: SearchPeriods) -> "FeatureTable":
        records = HistoryRecordsLoader(con).load(periods.warmup_from)
        rows = FlatRunnerFilter().apply(records.entries)
        rows = rows[rows["race_date"] >= pd.Timestamp(periods.discover_from)]
        # custom_binary の学習と同じく、正常に走って着順の無い行は除く（中止・失格は残す）。
        rows = rows[as_numbers(rows["finish"]).ge(1) | rows["abnormal"].isin(["4", "5"])]
        builder = SelectedFeatureBuilder(registry, tuple(registry.definitions), PredictionTiming.RACE_DAY)
        # custom_binary の学習と同じく、追加の元データ（券種オッズ）を出走の行に付けてから作る。
        rows = ExtraDataLoader(con).attach(rows, TargetScope.since(periods.discover_from).relation, builder.sources)
        frame = builder.build(records.with_entries(rows))
        return cls(rows[list(ROW_COLUMNS)].copy(), frame)

    @classmethod
    def load(cls, folder: Path) -> "FeatureTable":
        return cls(pd.read_pickle(folder / "rows.pkl"), pd.read_pickle(folder / "features.pkl"))

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        self.rows.to_pickle(folder / "rows.pkl")
        self.frame.to_pickle(folder / "features.pkl")
