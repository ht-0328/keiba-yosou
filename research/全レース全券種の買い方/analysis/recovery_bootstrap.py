"""開催日を単位に選び直して（ブートストラップ）、回収率の 90% の幅の下の端を出す。"""

from __future__ import annotations

import numpy as np

#: 道具の ``BootstrapInterval`` と同じ回数・乱数の種・幅。
ROUNDS, SEED, LOWER = 2000, 20260924, 0.05


class RecoveryBootstrap:
    """開催日 ``days`` 日を、同じ数だけ重複を許して ``ROUNDS`` 回選び直し、回収率（払戻 ÷ 投資）の下から 5% の点（90% の幅の下の端）を出す。

    選び直しの結果（各回で各日が何回選ばれたか）を先に作っておくので、候補がいくつあっても行列の掛け算で済む。
    ``lower(stakes, payouts)`` は、形 [候補, 開催日] の投資と払戻から、候補ごとの下の端を返す（投資が 0 の候補は NaN）。
    """

    def __init__(self, days: int, rounds: int = ROUNDS, seed: int = SEED) -> None:
        rng = np.random.default_rng(seed)
        picks = rng.integers(0, days, size=(rounds, days))
        self._counts = np.zeros((rounds, days))
        np.add.at(self._counts, (np.repeat(np.arange(rounds), days), picks.ravel()), 1.0)

    def lower(self, stakes: np.ndarray, payouts: np.ndarray) -> np.ndarray:
        stakes2 = np.atleast_2d(stakes)
        payouts2 = np.atleast_2d(payouts)
        resampled_stake = stakes2 @ self._counts.T      # [候補, 回]
        resampled_payout = payouts2 @ self._counts.T
        with np.errstate(divide="ignore", invalid="ignore"):
            rates = np.where(resampled_stake > 0, resampled_payout / resampled_stake, np.nan)
        lower = np.nanquantile(rates, LOWER, axis=1) if rates.size else np.array([])
        lower[stakes2.sum(axis=1) <= 0] = np.nan
        return lower
