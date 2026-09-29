"""区切りを順に回し、予測を1つの表にする。"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import pandas as pd
from 既存モデルの改善.analysis.windows import TestWindow

from .window_split import WindowSplit

#: 予測の表に残す列。
KEEP_COLUMNS: tuple[str, ...] = ("レースID", "開催日", "馬番", "確定の単勝人気", "3着以内")
#: 表にあれば残す、条件ごとに分けて見るための列（材料の表の名前のまま）。
INFO_COLUMNS: tuple[str, ...] = ("確定の単勝オッズ", "クラス", "芝ダ", "通算の出走数", "class_name", "surface", "runs_before")


class WalkForward:
    """区切りごとに ``model`` で学習して予測し、``score``（3着以内の確率）と ``区切り`` の列を付けた表を返す。

    ``model`` は ``predict(frame, columns, split)`` を持つもの（``LightGBMWindowModel`` など）。
    """

    def __init__(self, model, windows: Sequence[TestWindow]) -> None:
        self._model = model
        self._windows = tuple(windows)

    def run(self, frame: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, list[int]]:
        """（予測の表, 区切りごとの木の数）。"""
        parts, trees = [], []
        for window in self._windows:
            split = WindowSplit(window)
            score, tree_count = self._model.predict(frame, columns, split)
            kept = [*KEEP_COLUMNS, *(column for column in INFO_COLUMNS if column in frame.columns)]
            part = split.test(frame)[kept].copy()
            parts.append(part.assign(score=score, 区切り=window.name))
            trees.append(tree_count)
            print(f"  {self._model.name} / {window.name}: 木 {tree_count} 本", file=sys.stderr, flush=True)
        return pd.concat(parts, ignore_index=True), trees
