"""学習の流れの結果。"""

from dataclasses import dataclass
from pathlib import Path

from ..setting import ModelSettings


@dataclass(frozen=True)
class TrainedModel:
    """学習して保存したモデルの、設定・保存先・検証期間の成績（``scores`` と ``paybacks``）。"""

    settings: ModelSettings
    folder: Path
    validation: dict
