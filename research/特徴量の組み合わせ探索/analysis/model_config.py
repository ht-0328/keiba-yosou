"""モデルで探すときの1通りの設定（custom_binary の YAML 1つぶん）。"""

from dataclasses import dataclass

from yosou.custom_binary.feature.registry import FeatureRegistry
from yosou.custom_binary.settings import ModelSettings

from .search_periods import SearchPeriods

#: 目的ごとに、回収率を見る券種。勝利は単勝、馬券内は複勝。
BET_OF_TARGET = {"勝利": "単勝", "馬券内": "複勝"}


@dataclass(frozen=True)
class ModelConfig:
    name: str
    target: str
    features: tuple[str, ...]
    conditions: dict
    popularity: dict
    odds_baseline: bool = False
    #: 確かめる期間で、期待値の線（1.0〜1.5）の中だけから買い方を選ぶか。
    value_lines_only: bool = False

    @property
    def bet(self) -> str:
        return BET_OF_TARGET[self.target]

    def settings(self, registry: FeatureRegistry, periods: SearchPeriods) -> ModelSettings:
        values = {
            "name": self.name, "target": self.target, "timing": "当日", "popularity": self.popularity,
            "conditions": self.conditions, "odds_baseline": self.odds_baseline, "training": periods.training(),
        }
        return ModelSettings.from_values(values, self.features, registry)

    def yaml_values(self) -> dict:
        """custom_binary の YAML に書く値（features_file は別に書く）。"""
        return {"name": self.name, "target": self.target, "timing": "当日", "popularity": self.popularity,
                "conditions": self.conditions, "odds_baseline": self.odds_baseline}
