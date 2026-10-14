"""学習（train）が保存した、1つの予想・時点のモデルの記録。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yosou.shared.feature import PredictionTiming

from .development_model_kind import DevelopmentModelKind


@dataclass(frozen=True)
class SavedModel:
    """保存した1つの予想・時点のモデル。"""

    kind: DevelopmentModelKind
    timing: PredictionTiming
    folder: Path
    tree_counts: tuple[int, ...]
    order_lambda: float | None
