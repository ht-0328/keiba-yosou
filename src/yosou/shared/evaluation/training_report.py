"""学習の結果の入れ物。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..dataset import SplitData, TrainingPeriod
from ..feature import PredictionTiming
from .class_evaluation import ClassEvaluation
from .evaluation import Evaluation


@dataclass(frozen=True)
class TrainingReport:
    """学習の結果。

    - ``period``: 学習に使った期間（ウォームアップ・学習・検証・テストの始まりの日）。
    - ``split``: 時期で分けた学習データ・検証データ・テストデータ。
    - ``evaluations``: 検証データでの当たり具合（時点 × モデル）。二値分類なら ``Evaluation``、多クラス分類なら ``ClassEvaluation``。
    - ``model_folders``: 時点ごとの、モデルを保存したフォルダ。
    """

    period: TrainingPeriod
    split: SplitData
    evaluations: Sequence[Evaluation | ClassEvaluation]
    model_folders: dict[PredictionTiming, Path]
