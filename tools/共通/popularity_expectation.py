"""出走ごとに、人気から見た期待（同じ出走の集まりの中で、同じ単勝人気の馬がふつう出す勝率・複勝率）を付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PopularityGap:
    """人気から見た差（実際の率 − 人気から見た期待の率）と、その差の標準誤差。どちらも割合（0.012 = 1.2pt）。

    標準誤差は、各出走の当たる確率を期待の率とみなしたときの、平均の差のばらつき（√Σp(1−p) ÷ 頭数）。
    人気の無い出走は数えない。期待の側に無い人気（基準の集まりに居ない 17番人気 など）の出走も数えない。
    """

    runs: int
    gap: float
    std_error: float


class PopularityExpectation:
    """``runs``（``ReferenceRuns`` の表の一部）の中で、単勝人気ごとの勝率・複勝率を期待にする。

    延長の馬は人気薄に偏るように、比べる組ごとに人気の混ざり方が違う。そのまま率を比べると人気の差まで混ざるので、
    同じ人気の馬がふつう出す率からどれだけ上か下かで比べる。期待は渡した ``runs`` 全体（コース×馬場状態の節や、
    コースの全馬場状態）で数える。
    """

    def __init__(self, runs: pd.DataFrame) -> None:
        rated = runs[runs["popularity"].notna()]
        self._win = won(rated).groupby(rated["popularity"]).mean()
        self._top3 = placed(rated).groupby(rated["popularity"]).mean()

    def win_gap(self, runs: pd.DataFrame) -> PopularityGap:
        """``runs`` の勝率の、人気から見た差。"""
        rated = runs[runs["popularity"].notna()]
        return _gap(won(rated), rated["popularity"].map(self._win))

    def top3_gap(self, runs: pd.DataFrame) -> PopularityGap:
        """``runs`` の複勝率（3着以内の率）の、人気から見た差。"""
        rated = runs[runs["popularity"].notna()]
        return _gap(placed(rated), rated["popularity"].map(self._top3))


def won(runs: pd.DataFrame) -> pd.Series:
    """1着なら 1.0。着順の無い出走（競走中止・失格）は ``first`` が欠損値になることがあるので、0 にする。"""
    return runs["first"].astype("boolean").fillna(False).astype(float)


def placed(runs: pd.DataFrame) -> pd.Series:
    """3着以内なら 1.0（欠損値は 0）。"""
    return (runs["first"].astype("boolean") | runs["second"].astype("boolean") | runs["third"].astype("boolean")).fillna(False).astype(float)


def _gap(actual: pd.Series, expected: pd.Series) -> PopularityGap:
    known = expected.notna()
    actual, expected = actual[known], expected[known]
    count = len(actual)
    if count == 0:
        return PopularityGap(0, float("nan"), float("nan"))
    hits, chances = actual.to_numpy(dtype=float), expected.to_numpy(dtype=float)
    std_error = float(np.sqrt(np.sum(chances * (1 - chances))) / count)
    return PopularityGap(count, float(hits.mean() - chances.mean()), std_error)
