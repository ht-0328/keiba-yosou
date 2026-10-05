"""学習済みモデルのフォルダ1つ。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ModelFolder:
    """1つの学習済みモデル（``settings.json`` のあるフォルダ）。``relative`` は予想のモデルの置き場所からの相対パス（``1着/race_day`` など）。"""

    yosou: str
    relative: str
    updated_at: datetime
