"""中央の期待度の点数の候補: ◎ の1着の確率 ＋ 重み ×（単勝の期待値 − 1）の、重みを変えたもの。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import WIN_PROBABILITY, WIN_VALUE

from 地方の期待度.analysis.score_candidate import ScoreCandidate

#: 比べる重み（結果を見る前に決めた一覧）。1 が今の本番の式。地方で比べた重みと同じ並びに 1.5 を足した。
WEIGHTS: tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)


def weighted(weight: float) -> ScoreCandidate:
    """重み ``weight`` の点数の式。"""

    def compute(tops: pd.DataFrame) -> pd.Series:
        return tops[WIN_PROBABILITY].astype(float) + weight * (tops[WIN_VALUE].astype(float) - 1.0)

    return ScoreCandidate(f"重み {weight:g}", f"1着の確率 ＋ {weight:g} ×（単勝の期待値 − 1）", compute)


CANDIDATES: tuple[ScoreCandidate, ...] = tuple(weighted(weight) for weight in WEIGHTS)
