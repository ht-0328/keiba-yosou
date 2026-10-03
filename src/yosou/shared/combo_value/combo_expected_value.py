"""組み合わせの券種の買い目の期待値と確率を出す。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..betting import TicketType
from .horse_ratio import TOP3_RATIO, WIN_RATIO


class ComboExpectedValue:
    """買い目（組）の期待値を、市場が見た組の確率に「モデル ÷ 市場」の比を掛けて出す。

    市場が見た組の確率 = 払戻率 ÷ オッズ（組のオッズの逆数の合計が、およそ払戻率の逆数になるため）。
    モデルが見た組の確率 = 市場が見た組の確率 × 組の各位置の馬の比の積。
    期待値 = モデルが見た組の確率 × オッズ = 払戻率 × 比の積（オッズは消える）。

    比は、着順を区別する券種（馬単・3連単）では1着の位置に1着の比、2着以下の位置に3着以内の比を使い、
    順不同の券種（馬連・ワイド・3連複）では全部の位置に3着以内の比を使う。
    例: 3連単 ◎→○→▲ で、◎ の1着の比 1.3、○・▲ の3着以内の比 1.1・1.0 なら、期待値は 0.725 × 1.3 × 1.1 × 1.0 = 1.04。
    比の無い馬（市場の見立てが無い）を含む組は欠損値。
    """

    def of(self, ticket_type: TicketType, combos: Sequence[tuple[int, ...]], ratios: pd.DataFrame) -> np.ndarray:
        """``combos`` は組の並び（馬番の組。着順を区別する券種は1着から順）。``ratios`` は馬番を index にした ``HorseRatio.of`` の表。

        戻り値は組ごとの期待値（``combos`` と同じ並び）。
        """
        if not combos:
            return np.empty(0, dtype=float)
        spec = ticket_type.spec
        horses = np.asarray(combos, dtype=int)
        win_ratio = ratios[WIN_RATIO].reindex(horses.ravel()).to_numpy(dtype=float).reshape(horses.shape)
        top3_ratio = ratios[TOP3_RATIO].reindex(horses.ravel()).to_numpy(dtype=float).reshape(horses.shape)
        per_position = top3_ratio.copy()
        if spec.is_ordered:
            per_position[:, 0] = win_ratio[:, 0]
        return spec.payout_rate * per_position.prod(axis=1)

    def probability(self, value: pd.Series, odds: pd.Series) -> pd.Series:
        """モデルが見た組の確率 = 期待値 ÷ オッズ。オッズが無ければ欠損値。"""
        odds = pd.to_numeric(odds, errors="coerce").set_axis(value.index)
        return value.astype(float) / odds.where(odds > 0)
