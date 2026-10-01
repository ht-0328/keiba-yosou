"""回収率の下限（開催日を丸ごと取り直したときの、90%の幅の下側）。"""

import numpy as np
import pandas as pd

from .payback_rules import STAKE

#: 開催日を取り直す回数と、乱数の種（同じ結果が出るように固定する）。
BOOTSTRAP_ROUNDS = 1000
BOOTSTRAP_SEED = 0


class BootstrapLowerBound:
    """開催日を丸ごと取り直した回収率の、90%の幅の下側（5%点）。1日しか無ければ None。"""

    def of(self, days: np.ndarray, payouts: np.ndarray) -> float | None:
        frame = pd.DataFrame({"day": days, "payout": payouts}).groupby("day").agg(bets=("payout", "size"), paid=("payout", "sum"))
        if len(frame) < 2:
            return None
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        picks = rng.integers(0, len(frame), size=(BOOTSTRAP_ROUNDS, len(frame)))
        rates = frame["paid"].to_numpy()[picks].sum(axis=1) / (STAKE * frame["bets"].to_numpy()[picks].sum(axis=1))
        return float(np.quantile(rates, 0.05))
