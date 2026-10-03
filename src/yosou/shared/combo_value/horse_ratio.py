"""馬ごとの「モデル ÷ 市場」の比を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 出す列。1着の比（1着になる確率 ÷ オッズから見た勝率）と、3着以内の比（3着以内に入る確率 ÷ オッズから見た3着以内率）。
WIN_RATIO = "win_ratio"
TOP3_RATIO = "top3_ratio"


class HorseRatio:
    """馬ごとに、モデルの確率が市場の見立ての何倍かを出す。

    - 1着の比 = 1着になる確率 ÷ オッズから見た勝率。
    - 3着以内の比 = 3着以内に入る確率 ÷ オッズから見た3着以内率。
    例: 3着以内に入る確率 0.30・オッズから見た3着以内率 0.25 なら、3着以内の比は 1.2（市場より 2割高く見ている）。
    市場の見立てが無い（オッズの無い木曜・無投票）か 0 なら欠損値。1着の確率が無ければ（1着のモデルが無い）1着の比は欠損値。
    """

    def of(self, probability: pd.Series, market_top3: pd.Series, win_probability: pd.Series, market_win: pd.Series) -> pd.DataFrame:
        """行の並びと index は ``probability`` と同じ。列は ``WIN_RATIO``・``TOP3_RATIO``。"""
        return pd.DataFrame({
            WIN_RATIO: self._ratio(win_probability, market_win),
            TOP3_RATIO: self._ratio(probability, market_top3),
        }, index=probability.index)

    def _ratio(self, model: pd.Series, market: pd.Series) -> np.ndarray:
        model = pd.to_numeric(model, errors="coerce").to_numpy(dtype=float)
        market = pd.to_numeric(market, errors="coerce").to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(market > 0, model / market, np.nan)
        return ratio
