"""登録馬の確かめの結果の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class RegistrationCheckResult:
    """登録馬の確かめの結果。

    - ``table``: 1行 = 1頭の登録馬。レースID・開催日・競走名・馬ID・馬名・交流区分・3着以内に入る確率・1着になる確率・
      出走した・確定着順・確定の単勝人気・馬番（確定成績のもの）。予測できなかったレースは入らない。
    - ``skipped``: 予測できなかったレース（レースID, 理由）。
    - ``path``: 書いた表のファイル。
    """

    table: pd.DataFrame
    path: Path
    skipped: list[tuple[str, str]] = field(default_factory=list)
