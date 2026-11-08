"""区切りを古い順に回して、1つの作り方・1つの時点の予測の表と学習の記録をまとめる。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import chain

import pandas as pd

from 既存モデルの改善.analysis.windows.test_window import TestWindow

from .longshot_data import LongshotData
from .longshot_variant import LongshotVariant
from .longshot_window_trainer import LongshotWindowTrainer


class LongshotWalkForward:
    """``windows`` の各区切りで学び直し、テストの半年の予測をつなぐ。"""

    def __init__(self, trainer: LongshotWindowTrainer, windows: Sequence[TestWindow]) -> None:
        self._trainer = trainer
        self._windows = tuple(windows)

    def run(self, data: LongshotData, variant: LongshotVariant) -> tuple[pd.DataFrame, pd.DataFrame]:
        results = [self._trainer.run(data, window, variant) for window in self._windows]
        predictions = pd.concat([frame for frame, _ in results], ignore_index=True)
        log = pd.DataFrame(list(chain.from_iterable(rows for _, rows in results)))
        return predictions, log
