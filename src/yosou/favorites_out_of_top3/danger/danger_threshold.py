"""人気馬の「普段より危ない」の線を、検証期間で決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 線の候補（危険度 = 4着以下の確率 − オッズから見た4着以下の確率。0.01 = 1ポイント）。
CANDIDATES: tuple[float, ...] = tuple(round(value, 3) for value in np.arange(0.0, 0.205, 0.01))
#: 危険と判定する頭数の下限（これより少ない線は選ばない）。
_MIN_FLAGGED = 30


class DangerThreshold:
    """人気帯ごとに、「危険度がこの値以上なら危険」の線を検証期間で決める（既存モデルの修正計画の 1「人気馬の4着以下」）。

    危険度は「予想の4着以下の確率 − オッズから見た4着以下の確率（基準）」。同じオッズの馬より、どれだけ負けやすいか。
    線は、危険とした馬の実際の4着以下率が、同じ人気帯の全体をどれだけ上回るかを、頭数も考えて
    （差 × √頭数。偶然では出にくい差ほど大きい）いちばん大きくするものを選ぶ。危険とする馬が 30頭に満たない線は選ばない。
    テスト期間の結果は使わない。
    """

    def choose(self, danger: pd.Series, lost: pd.Series) -> float:
        """検証期間の危険度と実際の4着以下（1 か 0）から線を決める。どの線も条件に合わなければ NaN。"""
        base = float(lost.mean())
        scores = {threshold: self._score(danger, lost, threshold, base) for threshold in CANDIDATES}
        valid = {threshold: score for threshold, score in scores.items() if not np.isnan(score)}
        if not valid:
            return float("nan")
        return max(valid, key=valid.get)

    def _score(self, danger: pd.Series, lost: pd.Series, threshold: float, base: float) -> float:
        flagged = lost[danger >= threshold]
        if len(flagged) < _MIN_FLAGGED:
            return float("nan")
        return (float(flagged.mean()) - base) * np.sqrt(len(flagged))
