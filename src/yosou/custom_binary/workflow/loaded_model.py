"""予想に使う、保存したモデル一式。"""

from dataclasses import dataclass
from pathlib import Path

from yosou.shared.ml_model import EnsembleModel
from yosou.shared.place_value import PlacePriceEstimator

from ..feature.registry import FeatureRegistry
from ..setting import ModelSettings
from ..store import ModelStore


@dataclass(frozen=True)
class LoadedModel:
    """予想に使う、保存したモデル一式（設定・2つのモデルの平均・複勝の想定払戻倍率）。

    何レースも続けて予想するときは、1回だけ読んで使い回す。
    """

    settings: ModelSettings
    ensemble: EnsembleModel
    place_price: PlacePriceEstimator | None

    @classmethod
    def load(cls, models: Path, registry: FeatureRegistry) -> "LoadedModel":
        store = ModelStore(models)
        settings, ensemble = store.load(registry)
        return cls(settings, ensemble, store.place_price())
