"""ワイドで受け取る額の見込みを、年ごとに作る。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..ticket import PlacePriceEstimator


class WidePriceBook:
    """ワイドの受け取る額の見込み = 最低オッズ × 帯ごとの倍率（複勝と同じ見積もり方）。

    ワイドの払戻は、一緒に3着以内に来た馬で変わるので、買う時点では「最低〜最高」の幅しか分からない。
    倍率は、評価する年より前の年の、当たったワイドの「払戻 ÷ 最低オッズ」から作る。
    """

    def __init__(self, tickets_dir: Path, payouts: pd.DataFrame, first_year: int, last_year: int) -> None:
        frames = []
        for year in range(first_year, last_year + 1):
            odds = pd.read_parquet(tickets_dir / f"wide_{year}.parquet")
            hits = odds.merge(payouts, on=["rid", "h1", "h2"], how="inner")
            frames.append(hits.assign(year=year)[["year", "odds", "payout"]])
        self._hits = pd.concat(frames, ignore_index=True)

    def price(self, odds: pd.DataFrame, year: int) -> pd.Series:
        """``odds`` の各行（最低オッズ）の、受け取る額の見込み。"""
        train = self._hits[self._hits["year"] < year]
        estimator = PlacePriceEstimator().fit(train["odds"], train["payout"], pd.Series(1, index=train.index))
        return estimator.estimate(odds["odds"])
