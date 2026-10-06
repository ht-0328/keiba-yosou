"""テスト期間の確かめの結果の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..dataset import TrainingData, TrainingPeriod
from ..feature import PredictionTiming
from .evaluation import Evaluation


@dataclass(frozen=True)
class BacktestReport:
    """テスト期間の確かめ（``BacktestWorkflow``）の結果（地方の設計書 16 の 4）。

    - ``period``: 使った期間（テスト期間はその最後の区切りから）。
    - ``test``: テスト期間の行（3着以内の形の学習データ）。
    - ``evaluations``: 目的変数の名前（3着以内・1着）→ 時点ごと・名前ごとの当たり具合（モデル2つ・平均・市場の確率）。
    - ``prediction_paths``: 目的変数の名前 → 時点 → 書いた予測の表のファイル（道具「印の成績」が読む形）。
    """

    period: TrainingPeriod
    test: TrainingData
    evaluations: dict[str, list[Evaluation]] = field(default_factory=dict)
    prediction_paths: dict[str, dict[PredictionTiming, Path]] = field(default_factory=dict)
