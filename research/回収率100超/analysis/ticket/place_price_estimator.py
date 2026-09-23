"""複勝の「発表オッズ」から、実際に受け取る払戻の倍率を見積もる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 見積もりを分ける、最低オッズの区切り。
DEFAULT_BANDS: tuple[float, ...] = (0.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 10000.0)


class PlacePriceEstimator:
    """複勝で実際に受け取る払戻倍率を、発表の最低オッズから見積もる。

    JRA の複勝は、3着以内に入った3頭の組み合わせによって払戻が変わるので、買う時点では
    「最低オッズ〜最高オッズ」の幅しか分からない。最低オッズをそのまま期待値の計算に使うと、
    期待値を 2割ほど低く見積もることになる（実測で、的中した複勝の払戻は最低オッズの平均 1.19倍）。

    そこで、過去の的中した複勝から「払戻 ÷ 最低オッズ」の平均を最低オッズの帯ごとに求め、
    それを掛けた値を想定の払戻倍率にする。学習に使う期間だけで推定し、評価する期間では使わない。
    """

    def __init__(self, bands: tuple[float, ...] = DEFAULT_BANDS) -> None:
        self._bands = bands
        self._multiplier: pd.Series | None = None

    def fit(self, lowest_odds: pd.Series, payout: pd.Series, placed: pd.Series) -> PlacePriceEstimator:
        """的中した複勝だけを使って、帯ごとの倍率を求める。"""
        hit = placed.astype(bool) & (payout > 0) & lowest_odds.notna() & (lowest_odds > 0)
        ratio = payout[hit] / (100.0 * lowest_odds[hit])
        band = pd.cut(lowest_odds[hit], self._bands)
        self._multiplier = ratio.groupby(band, observed=True).mean()
        return self

    def estimate(self, lowest_odds: pd.Series) -> pd.Series:
        """想定の払戻倍率（発表の最低オッズ × 帯ごとの倍率）。"""
        if self._multiplier is None:
            raise RuntimeError("まだ推定していません（fit を先に呼んでください）")
        factor = pd.cut(lowest_odds, self._bands).map(self._multiplier).astype(float)
        return lowest_odds * factor.fillna(float(np.nanmean(self._multiplier)))
