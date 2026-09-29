"""学習の流れを進める。"""

from pathlib import Path

from 共通 import db

from yosou.shared.dataset import TrainingData

from ..dataset import CustomDataset
from ..evaluation import ModelReport, PlacePriceFit
from ..feature.registry import FeatureRegistry
from ..store import MODELS_ROOT, ModelStore
from ..setting import ModelSettings
from .ensemble_fitter import EnsembleFitter
from .trained_model import TrainedModel


class TrainingWorkflow:
    """学習の流れ（設計書 05 の図1）。設定を読む → 学習データを作る → 元DB を閉じる → 学ぶ → 検証期間で評価する → 保存する。

    モデルは ``<models_root>/<設定の name>/`` に保存する（省略すると ``reports/特徴量と条件を選んで予想/``）。
    同じ名前の保存先があれば、元DB を開く前に止める。
    """

    def __init__(self, registry: FeatureRegistry, database: Path | None = None, models_root: Path | None = None) -> None:
        self._registry = registry
        self._database = database
        self._models_root = MODELS_ROOT if models_root is None else models_root

    def run(self, config: Path) -> TrainedModel:
        settings = ModelSettings.load(config, self._registry)
        store = ModelStore(self._models_root / settings.name)
        store.check_new()
        with db.open_db(self._database) as con:
            data = CustomDataset(con, settings, self._registry).training()
        # 元DBは読み終えたら閉じる。モデルの学習中にDBロックを保持しない。
        validation = self.fit_and_save(data, settings, store)
        return TrainedModel(settings, store.root, validation)

    def fit_and_save(self, data: TrainingData, settings: ModelSettings, store: ModelStore) -> dict:
        """作った学習データで学び、検証期間の成績と一緒に保存する。検証期間の成績を返す。"""
        store.check_new()
        ensemble, train, valid = EnsembleFitter().fit(data, settings)
        validation = ModelReport().of(ensemble, valid, settings.target, train)
        store.save(settings, self._registry, list(ensemble.members), validation,
                   {"train": len(train), "validation": len(valid)}, PlacePriceFit().fit(train))
        return validation
