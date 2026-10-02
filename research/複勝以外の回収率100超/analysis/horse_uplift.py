"""モデルが見た「この馬は市場より来る」の度合いを、組の確率に掛ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 回収率100超.analysis.tickets import MAX_HORSES, TicketKind

#: 比の上限と下限。確率の小さい馬で比が極端になり、組の確率を振り回すのを防ぐ。
_RATIO_BOUNDS = (0.2, 5.0)


class HorseUplift:
    """馬ごとの比（モデルの3着以内の確率 ÷ 単勝から見た3着以内の確率）の ``strength`` 乗を、組の各馬ぶん掛ける。

    掛けたあと、表の合計が掛ける前と同じになるようにそろえ直す。``strength`` が 0 なら、表は変わらない。
    例: 馬連の 1-5 で、1番の比が 1.2、5番の比が 1.5、strength 1 なら、1.8倍してからそろえ直す。
    予測の無いレースは None（比べる相手をそろえるため、どの作り方でも同じレースだけを使う）。
    """

    def __init__(self, rid: pd.Series, horse_no: pd.Series, model: pd.Series, market: pd.Series,
                 strength: float) -> None:
        valid = model.notna() & market.notna() & (market > 0) & horse_no.between(1, MAX_HORSES)
        codes, races = pd.factorize(rid[valid])
        self._row_of = pd.Series(np.arange(len(races)), index=races)
        ratio = (model[valid] / market[valid]).clip(*_RATIO_BOUNDS) ** strength
        self._ratios = np.ones((len(races), MAX_HORSES))
        self._ratios[codes, horse_no[valid].to_numpy(dtype=np.int64) - 1] = ratio.to_numpy()

    def apply(self, kind: TicketKind, rid: int, table: np.ndarray) -> np.ndarray | None:
        row = self._row_of.get(rid)
        if row is None:
            return None
        weights = self._weights(self._ratios[row], kind.horses)
        adjusted = table * weights
        total = adjusted.sum()
        return adjusted * (table.sum() / total) if total > 0 else table

    def _weights(self, ratio: np.ndarray, horses: int) -> np.ndarray:
        weights = ratio
        for _ in range(horses - 1):
            weights = np.multiply.outer(weights, ratio)
        return weights.ravel()
