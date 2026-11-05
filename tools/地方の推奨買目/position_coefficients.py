"""1着・2着・3着の条件つきロジットの係数（特徴量の名前と値の組）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PositionCoefficients:
    """``first``・``second``・``third`` は特徴量の名前 → 係数。``rows`` は表に出す形。"""

    first: dict[str, float]
    second: dict[str, float]
    third: dict[str, float]

    @classmethod
    def of(cls, names: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]], betas: tuple[np.ndarray, np.ndarray, np.ndarray]) -> PositionCoefficients:
        return cls(*[dict(zip(n, (float(v) for v in b), strict=True)) for n, b in zip(names, betas, strict=True)])

    def vector(self, position: int) -> np.ndarray:
        return np.array(list((self.first, self.second, self.third)[position].values()), dtype=np.float64)

    def rows(self, label: str) -> list[dict]:
        """表の行（当てはめ・着・特徴量・係数）。"""
        return [{"当てはめ": label, "着": name, "特徴量": feature, "係数": round(value, 3)}
                for name, coefficients in (("1着", self.first), ("2着", self.second), ("3着", self.third)) for feature, value in coefficients.items()]
