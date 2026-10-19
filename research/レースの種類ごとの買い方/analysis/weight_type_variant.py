"""今の本番の材料に、重量種別（ハンデか・別定か）の2つの列を足す作り方（docs/01 の 7 の「材料を足す」）。"""

from __future__ import annotations

from dataclasses import dataclass, replace

from yosou.shared.dataset import TrainingData

from 既存モデルの改善.analysis.variants import ModelVariant

from .kind_columns import WEIGHT_TYPE_COLUMN

#: 足す材料の列（1 か 0）。どちらでもないのが馬齢・定量。
WEIGHT_TYPE_FEATURES: dict[str, str] = {"is_handicap": "ハンデ", "is_special_weight": "別定"}


@dataclass(frozen=True)
class WeightTypeVariant(ModelVariant):
    """``ModelVariant`` と同じ学び方で、時点の列にしてから、評価用の列 ``WEIGHT_TYPE_COLUMN``（``KindColumns`` が足す）から作った
    ``WEIGHT_TYPE_FEATURES`` の列を特徴量に足す。特徴量の一覧（catalog）に無い新しい列なので、``prepare`` で足す。"""

    def prepare(self, data: TrainingData) -> TrainingData:
        timed = data.for_timing(self.timing)
        kind = timed.evaluation[WEIGHT_TYPE_COLUMN]
        added = timed.features.assign(**{name: (kind == value).astype(float).to_numpy() for name, value in WEIGHT_TYPE_FEATURES.items()})
        columns = [*self.columns, *WEIGHT_TYPE_FEATURES]
        missing = [column for column in columns if column not in added.columns]
        if missing:
            raise ValueError(f"{self.name}: 学習データに無い列があります: {'・'.join(missing)}")
        baseline = timed.baseline if self.uses_baseline else None
        return replace(timed, features=added[columns], baseline=baseline)
