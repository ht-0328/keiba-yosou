"""テスト用の偽の2つのモデル: 特徴量を見ずに、決めた値をそのまま付ける。"""

from __future__ import annotations

import pandas as pd

from 地方の直前の買い目 import late_columns as c


class FakeModels:
    """``likeness``・``payback`` は 馬番 → 値。無い馬は 0。"""

    def __init__(self, likeness: dict[int, float], payback: dict[int, float]) -> None:
        self._likeness = likeness
        self._payback = payback

    def score(self, features: pd.DataFrame) -> pd.DataFrame:
        scored = features.copy()
        scored[c.LIKENESS] = scored[c.HORSE_NO].map(self._likeness).fillna(0.0)
        scored[c.PAYBACK] = scored[c.HORSE_NO].map(self._payback).fillna(0.0)
        return scored
