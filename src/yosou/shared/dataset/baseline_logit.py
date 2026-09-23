"""目的変数の基準（ロジット）の値。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..feature import PredictionTiming


@dataclass(frozen=True)
class BaselineLogit:
    """モデルが出発点にする、目的変数が 1 になる基準の確率（ロジット）。1行ごとの値と、その値が分かる最初の時点。

    例: オッズから見た3着以内率が 0.40 の馬の値は log(0.40 ÷ 0.60) ≒ −0.41。モデルは、この値に、近走や適性から
    見た上げ下げ（例: +0.33）を足した値を確率に戻して出す（0.40 → 0.48）。LightGBM では ``init_score``、
    CatBoost では ``baseline`` として渡す（既存モデルの修正計画の 1・2）。

    オッズから作る基準は、オッズが分かる前日からしか使えない。``for_timing`` は、その時点で使えなければ None を返す。
    """

    values: pd.Series
    known_from: PredictionTiming

    def for_timing(self, timing: PredictionTiming) -> BaselineLogit | None:
        """その時点で使える基準。まだ分からない時点（木曜）なら None。"""
        if timing.is_at_or_after(self.known_from):
            return self
        return None

    def at(self, rows: pd.Series | pd.Index) -> BaselineLogit:
        """行を選んだ基準（真偽の列か、index の並び）。"""
        if isinstance(rows, pd.Series):
            return BaselineLogit(self.values[rows], self.known_from)
        return BaselineLogit(self.values.loc[rows], self.known_from)

    def array(self) -> np.ndarray:
        """ライブラリに渡す形（小数の1次元の配列）。"""
        return self.values.to_numpy(dtype="float64")

    def probabilities(self) -> pd.Series:
        """基準を確率に戻した値（オッズから見た確率）。"""
        return 1.0 / (1.0 + np.exp(-self.values))
