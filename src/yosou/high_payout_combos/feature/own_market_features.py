"""その券種の市場から作る材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .column_names import LOG_Q, LOG_T, ODDS

#: 作る材料。``log_q`` はその券種のオッズから見た組の確率の対数、``log_t`` は3連単の市場から足し合わせた確率の対数。
LOG_ODDS, FEATURE_LOG_Q, FEATURE_LOG_T, TRIFECTA_GAP = "log_odds", "log_q", "log_t", "d_t"
NAMES: tuple[str, ...] = (LOG_ODDS, FEATURE_LOG_Q, FEATURE_LOG_T, TRIFECTA_GAP)


class OwnMarketFeatures:
    """市場の表の行（列 ``odds``・``log_own``・``log_trifecta``）から、その券種の市場の材料を作る。

    - ``log_odds``: log(オッズ)。例: 20倍 → 3.00。
    - ``log_q``・``log_t``: その券種の市場の確率と、3連単の市場から見た確率の対数。
    - ``d_t``: log_t − log_q（3連単の市場が、その券種の市場より高く見ている分）。
    行の並びと index は ``rows`` と同じ。
    """

    def of(self, rows: pd.DataFrame) -> pd.DataFrame:
        log_q = rows[LOG_Q].to_numpy(dtype=float)
        log_t = rows[LOG_T].to_numpy(dtype=float)
        return pd.DataFrame({
            LOG_ODDS: np.log(rows[ODDS].to_numpy(dtype=float)),
            FEATURE_LOG_Q: log_q,
            FEATURE_LOG_T: log_t,
            TRIFECTA_GAP: log_t - log_q,
        }, index=rows.index)
