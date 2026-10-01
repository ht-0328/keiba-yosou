"""分位点回帰の 80% の幅を広げる（狭める）倍率。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import numpy as np

#: 倍率を書くファイルの名前の後ろ（モデルのファイルの名前に付ける）。
_WIDTH_SUFFIX = ".width.json"


@dataclass(frozen=True)
class IntervalWidth:
    """10%・50%・90% の値のうち、真ん中の値から下の端・上の端までの距離に掛ける倍率（設計書 10 の 4.・16 の 2.）。

    ``lower`` は真ん中から 10% の値まで、``upper`` は真ん中から 90% の値までの距離に掛ける。1.0 なら元のまま。
    検証データで、幅に入る割合が 80% に近くなるように決める（``IntervalWidthFitter``）。
    """

    lower: float = 1.0
    upper: float = 1.0

    def apply(self, quantiles: np.ndarray) -> np.ndarray:
        """行数 × 3（10%・50%・90%）の値を、行ごとに小さい順に並べてから、端の距離に倍率を掛けたもの。"""
        ordered = np.sort(np.asarray(quantiles, dtype="float64"), axis=1)
        low, middle, high = ordered[:, 0], ordered[:, 1], ordered[:, 2]
        return np.column_stack([middle - self.lower * (middle - low), middle, middle + self.upper * (high - middle)])

    def save(self, model_path: Path) -> None:
        """モデルのファイルの隣の小さな JSON に書く（設計書 12・13 の 6）。"""
        self._path(model_path).write_text(json.dumps({"lower": self.lower, "upper": self.upper}) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, model_path: Path) -> Self:
        """モデルのファイルの隣の JSON を読む。無ければ（倍率を決める前に保存したモデル）元のままの倍率。"""
        path = cls._path(model_path)
        if not path.exists():
            return cls()
        saved = json.loads(path.read_text(encoding="utf-8"))
        return cls(float(saved["lower"]), float(saved["upper"]))

    @staticmethod
    def _path(model_path: Path) -> Path:
        return Path(model_path).with_name(Path(model_path).name + _WIDTH_SUFFIX)
