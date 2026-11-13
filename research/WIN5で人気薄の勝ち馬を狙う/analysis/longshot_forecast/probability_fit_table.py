"""人気薄の1着の確率の当たり具合の表: 対数損失と、確率の合計 ÷ 実際に勝った数。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

_EDGE = 1e-6


@dataclass(frozen=True)
class ProbabilityFitTable:
    """``frame`` は ``EvaluationFrame`` の表。``columns`` は確率の列の名前。対数損失は小さいほど良い（オッズから見た勝率と比べる）。"""

    def build(self, frame: pd.DataFrame, columns: Sequence[str], title: str) -> Table:
        won = frame["won"].to_numpy(dtype=float)
        rows = [self._row(name, frame[name].to_numpy(dtype=float), won) for name in columns]
        return Table(["確率", "対数損失（1頭あたり）", "確率の合計", "実際に勝った数", "確率の合計 ÷ 実際"], rows, title=title,
                     note=f"人気薄 {len(frame):,}頭。対数損失は小さいほど良い。確率の合計 ÷ 実際 が 1 に近いほど、確率の大きさが合っている。")

    @staticmethod
    def _row(name: str, probability: np.ndarray, won: np.ndarray) -> list[object]:
        clipped = np.clip(probability, _EDGE, 1 - _EDGE)
        loss = -np.mean(won * np.log(clipped) + (1 - won) * np.log(1 - clipped))
        total, actual = float(probability.sum()), float(won.sum())
        return [name, f"{loss:.5f}", f"{total:.1f}", int(actual), f"{total / actual:.2f}" if actual else ""]
