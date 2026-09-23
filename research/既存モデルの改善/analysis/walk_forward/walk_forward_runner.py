"""区切りを順に回して、予測の表と学習の記録をまとめる。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from itertools import chain

import pandas as pd

from yosou.shared.dataset import TrainingData

from ..variants import ModelVariant
from ..windows import TestWindow
from .window_trainer import WindowTrainer


class WalkForwardRunner:
    """区切り（``windows``）を古い順に回し、1つの作り方の予測の表と学習の記録をまとめる。進み具合は標準エラーに出す。"""

    def __init__(self, trainer: WindowTrainer, windows: Sequence[TestWindow]) -> None:
        self._trainer = trainer
        self._windows = tuple(windows)

    def run(self, data: TrainingData, variant: ModelVariant) -> tuple[pd.DataFrame, pd.DataFrame]:
        """（予測の表, 学習の記録の表）。"""
        results = [self._one(data, window, variant) for window in self._windows]
        predictions = pd.concat([frame for frame, _ in results], ignore_index=True)
        log = pd.DataFrame(list(chain.from_iterable(rows for _, rows in results)))
        return predictions, log

    def _one(self, data: TrainingData, window: TestWindow,
             variant: ModelVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        print(f"{variant.model} / {variant.name} / {window.name}: 学習しています …", file=sys.stderr, flush=True)
        frame, rows = self._trainer.run(data, window, variant)
        seconds = sum(float(row["2つのモデルの学習の秒"]) for row in rows) / 2
        print(f"{variant.model} / {variant.name} / {window.name}: {len(frame)}行・{seconds:.0f}秒", file=sys.stderr, flush=True)
        return frame, rows
