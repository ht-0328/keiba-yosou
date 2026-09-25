"""券種オッズから見た、馬ごとの確率（3連単から見た勝率など）。"""

from collections.abc import Mapping

import pandas as pd

from yosou.shared.feature import EntryRecords, PredictionTiming
from yosou.shared.feature.feature_kind import FeatureKind

from ..extra_data import PoolProbabilitySource
from ..repository import PoolSpec


class PoolProbability:
    """その券種の全買い目の 1/オッズ をレース内で合計1にそろえ、その馬が入った買い目だけ足した値。

    例: 3連複で4番を含む買い目の確率の合計が 0.14 なら、「3連複から見た3着以内率」は 0.14。
    元DB の券種オッズ（追加の元データ「券種オッズ」）から作るので、オッズがそろう当日から使える。
    """

    kind = FeatureKind.NUMERIC
    known_from = PredictionTiming.RACE_DAY
    dependencies: tuple[str, ...] = ()
    sources = (PoolProbabilitySource.name,)

    def __init__(self, spec: PoolSpec) -> None:
        self.spec = spec
        self.name = spec.name
        self.description = f"{spec.name.split('から')[0]}の全買い目のオッズから、この馬が入った買い目の確率を足した値"

    def compute(self, records: EntryRecords, dependencies: Mapping[str, pd.Series]) -> pd.Series:
        return records.entries[self.spec.column].astype("float64")
