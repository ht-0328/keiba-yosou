"""開催日を単位に選び直して（ブートストラップ）、利益の下の端を出す。"""

from __future__ import annotations

import numpy as np

#: 道具の ``BootstrapInterval`` と同じ回数・乱数の種。
ROUNDS, SEED = 2000, 20260924
#: 利益の下の端に使う点（90% の幅の下の端 = 5% 点）。
LOWER = 0.05


class ProfitBootstrap:
    """``days`` 日の開催日を、同じ数だけ重複を許して選び直すことを ``ROUNDS`` 回くり返し、利益の合計の 5% 点を出す。

    選び直しの結果（各回で各日が何回選ばれたか）を先に作っておくので、決まりの候補がいくつあっても、行列の掛け算1回で済む。
    例: 3日の利益が 1,000円・−500円・−300円なら、選び直した合計の分布の下から 5% の値を返す。
    """

    def __init__(self, days: int, rounds: int = ROUNDS, seed: int = SEED) -> None:
        rng = np.random.default_rng(seed)
        picks = rng.integers(0, days, size=(rounds, days))
        self._counts = np.zeros((rounds, days))
        np.add.at(self._counts, (np.repeat(np.arange(rounds), days), picks.ravel()), 1.0)

    def lower(self, profit: np.ndarray) -> np.ndarray:
        """``profit`` は [開催日, 候補] の利益（円）。候補ごとの利益の合計の 5% 点。"""
        return np.quantile(self._counts @ profit, LOWER, axis=0)

    def lower_rate(self, stake: np.ndarray, payout: np.ndarray) -> np.ndarray:
        """``stake``・``payout`` は [開催日, 候補] の賭け金と払戻（円）。候補ごとの回収率の 5% 点（今の本番の決まりを選んだ基準）。"""
        stakes = self._counts @ stake
        with np.errstate(invalid="ignore", divide="ignore"):
            rates = (self._counts @ payout) / np.where(stakes > 0, stakes, np.nan)
        return np.nanquantile(rates, LOWER, axis=0)
