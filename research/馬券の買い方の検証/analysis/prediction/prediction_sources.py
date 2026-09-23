"""4つの予想モデルの ``PredictionSource`` の一覧。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from yosou.favorites_out_of_top3.dataset import dataset_builder as favorites_builder
from yosou.favorites_out_of_top3.workflow import PROBABILITY as FAVORITES_PROBABILITY
from yosou.form_aptitude_top3.dataset import dataset_builder as form_builder
from yosou.form_aptitude_top3.workflow import PROBABILITY as FORM_PROBABILITY
from yosou.longshots_in_top3.dataset import dataset_builder as longshots_builder
from yosou.longshots_in_top3.workflow import PROBABILITY as LONGSHOTS_PROBABILITY
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.upset_level.dataset import race_dataset_builder
from yosou.upset_level.workflow import model_repositories

from .batch_predictor import BatchPredictor
from .prediction_source import PredictionSource
from .race_batch_predictor import RaceBatchPredictor
from .runner_batch_predictor import RunnerBatchPredictor

#: 予想のパッケージ名（``reports/<名前>/models`` と出力の CSV の名前）。
FORM_APTITUDE = "form_aptitude_top3"
FAVORITES = "favorites_out_of_top3"
LONGSHOTS = "longshots_in_top3"
UPSET_LEVEL = "upset_level"


def _runner_predictor(probability_column: str) -> Callable[[Path], BatchPredictor]:
    """1頭ごとの予想の ``RunnerBatchPredictor`` を作る関数（確率の列名だけが予想ごとに違う）。"""
    def make(models_root: Path) -> BatchPredictor:
        return RunnerBatchPredictor(ModelRepository(models_root, MEMBER_TYPES), probability_column)
    return make


def _race_predictor(models_root: Path) -> BatchPredictor:
    """荒れ具合の予想の ``RaceBatchPredictor``（券種ごとのモデルの置き場を持つ）。"""
    return RaceBatchPredictor(model_repositories(models_root))


#: 4モデルの一覧（出力の順）。
SOURCES: tuple[PredictionSource, ...] = (
    PredictionSource(FORM_APTITUDE, "近走と適性から3着以内を予想", form_builder, _runner_predictor(FORM_PROBABILITY)),
    PredictionSource(FAVORITES, "人気馬が4着以下になるかを予想", favorites_builder, _runner_predictor(FAVORITES_PROBABILITY)),
    PredictionSource(LONGSHOTS, "穴馬が3着以内に入るかを予想", longshots_builder, _runner_predictor(LONGSHOTS_PROBABILITY)),
    PredictionSource(UPSET_LEVEL, "レースの荒れ具合を4段階で予想", race_dataset_builder, _race_predictor),
)
#: 名前の一覧（コマンドの ``--only`` の選択肢）。
SOURCE_NAMES: tuple[str, ...] = tuple(source.name for source in SOURCES)


def source_named(name: str) -> PredictionSource:
    """名前から ``PredictionSource`` を返す。知らなければ ``LookupError``。"""
    for source in SOURCES:
        if source.name == name:
            return source
    raise LookupError(f"知らない予想の名前です: {name}（{' / '.join(SOURCE_NAMES)}）")
