"""1つの目的の、オッズの動きの直しの重み。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OddsMoveWeights:
    """切片と、材料（``OddsMoveFeatures`` の列の並び）ごとの重み。直したロジット = 今のロジット ＋ 切片 ＋ 材料 · 重み。"""

    intercept: float
    move: float
    move_by_log_odds: float
    has_eve: float

    @classmethod
    def of(cls, values: np.ndarray) -> OddsMoveWeights:
        """切片・材料の重みの順の配列から作る。"""
        return cls(*(float(value) for value in values))

    def slopes(self) -> np.ndarray:
        return np.array([self.move, self.move_by_log_odds, self.has_eve])

    def to_dict(self) -> dict[str, float]:
        return {"切片": self.intercept, "オッズの動き": self.move, "オッズの動き×log(オッズ)": self.move_by_log_odds, "前日のオッズがあるか": self.has_eve}

    @classmethod
    def from_dict(cls, saved: dict[str, float]) -> OddsMoveWeights:
        return cls(saved["切片"], saved["オッズの動き"], saved["オッズの動き×log(オッズ)"], saved["前日のオッズがあるか"])
