"""予想ごと・時点ごとの学習済みモデルを、ファイルに読み書きする。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.shared.setting import HyperparameterSettings

from ..ml_model import FinishForecaster
from .development_model_kind import DevelopmentModelKind
from .kind_trainer import MEMBER_TYPES


class KindModelStore:
    """学習済みモデルを ``<root>/<予想>/<時点>/`` に書き、読む（設計書 04 の 4・12・13 の 6）。

    予想ごとに共通の ``ModelRepository`` を1つ作り、置き場所とモデルのクラスを変える。⑦ は、同じフォルダに
    2着・3着の割り当てのならしの指数 λ も書く。モデルは JV-Data から作ったものなので、``root`` は Git の対象外にする。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def save(self, kind: DevelopmentModelKind, timing: PredictionTiming, members: list[Any],
             settings: HyperparameterSettings, order_lambda: float | None) -> Path:
        folder = self._repository(kind).save(timing, members, settings)
        if order_lambda is not None:
            FinishForecaster(EnsembleModel(members), order_lambda).save_lambda(folder)
        return folder

    def load(self, kind: DevelopmentModelKind, timing: PredictionTiming) -> list[Any]:
        """その予想・時点の2つのモデル。無ければ ``FileNotFoundError``（先に train で学習する）。"""
        return self._repository(kind).load(timing)

    def load_lambda(self, timing: PredictionTiming) -> float:
        """⑦ の、その時点の λ。"""
        return FinishForecaster.load_lambda(self._root / DevelopmentModelKind.FINISH.folder / timing.value)

    def _repository(self, kind: DevelopmentModelKind) -> ModelRepository:
        return ModelRepository(self._root / kind.folder, MEMBER_TYPES[kind.spec.family])
