"""3着以内の確率を、複勝が当たる確率に直す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 複勝が2着までになる頭数の上限（7頭以下は2着まで）。
_SMALL_FIELD_UP_TO = 7


class PlaceHitProbability:
    """3着以内の確率を、複勝が当たる確率に直す（既存モデルの修正計画の 2「3着以内と複勝的中」）。

    8頭以上のレースは、複勝は3着まで当たりなので、3着以内の確率そのまま。7頭以下は2着までなので、
    オッズから見た「2着以内率 ÷ 3着以内率」の比を掛けて下げる。例: 3着以内の確率 0.50 で、オッズから見た
    2着以内率 0.30・3着以内率 0.45 なら、0.50 × 0.30 ÷ 0.45 ≒ 0.33。
    """

    def of(self, top3: pd.Series, field_size: pd.Series, top2_rate: pd.Series, top3_rate: pd.Series) -> pd.Series:
        ratio = (top2_rate / top3_rate.where(top3_rate > 0)).clip(upper=1.0).fillna(1.0)
        is_small = pd.to_numeric(field_size, errors="coerce") <= _SMALL_FIELD_UP_TO
        return pd.Series(np.where(is_small, top3 * ratio, top3), index=top3.index)
