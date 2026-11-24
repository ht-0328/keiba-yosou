"""Harville の式で出した組の確率から作る材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import LOG_Q
from .combo_members import ComboMembers
from .harville_probability import HarvilleProbability
from .material_names import MARKET_WIN_SHARE, WIN_SHARE
from .wide_pair_probability import WidePairProbability

#: 作る材料。``hv`` は予想の1着の確率から、``hw`` は単勝オッズから見た勝率から出した組の確率。``d_`` はその券種の市場の確率の対数との差。
LOG_HV, HV_GAP, LOG_HW, HW_GAP = "log_hv", "d_hv", "log_hw", "d_hw"
NAMES: tuple[str, ...] = (LOG_HV, HV_GAP, LOG_HW, HW_GAP)
#: 対数を取る前の組の確率の下限。
_MIN_PROBABILITY = 1e-12


class HarvilleFeatures:
    """組の確率を、予想の1着の確率（``pwn``）と単勝オッズから見た勝率（``mwn``）のそれぞれから Harville の式で出して、材料にする。

    馬単・3連単は着順どおり、馬連・3連複は全部の並びの和、ワイドは「2頭とも3着以内」（3頭目を全部の馬で足す）。
    例: 予想の1着の確率が 0.5・0.3・0.2 の3頭の馬単 1→2 は 0.3 なので ``log_hv`` は log 0.3 ≒ −1.20。
    行の並びと index は ``rows`` と同じ。
    """

    def __init__(self) -> None:
        self._harville = HarvilleProbability()
        self._wide = WidePairProbability()

    def of(self, ticket_type: TicketType, rows: pd.DataFrame, members: ComboMembers, materials: pd.DataFrame) -> pd.DataFrame:
        """``rows`` はその券種の市場の表の行、``members`` はその行の組の馬の材料、``materials`` は馬ごとの材料の表（ワイドだけが使う）。"""
        log_q = rows[LOG_Q].to_numpy(dtype=float)
        log_model = self._log_probability(ticket_type, rows, members, materials, WIN_SHARE)
        log_market = self._log_probability(ticket_type, rows, members, materials, MARKET_WIN_SHARE)
        return pd.DataFrame({
            LOG_HV: log_model, HV_GAP: log_model - log_q, LOG_HW: log_market, HW_GAP: log_market - log_q,
        }, index=rows.index)

    def _log_probability(self, ticket_type: TicketType, rows: pd.DataFrame, members: ComboMembers, materials: pd.DataFrame,
                         share: str) -> np.ndarray:
        return np.log(np.clip(self._probability(ticket_type, rows, members, materials, share), _MIN_PROBABILITY, None))

    def _probability(self, ticket_type: TicketType, rows: pd.DataFrame, members: ComboMembers, materials: pd.DataFrame,
                     share: str) -> np.ndarray:
        if ticket_type is TicketType.WIDE:
            return self._wide.of(rows, materials, share)
        shares = members.in_combo_order(share)
        if ticket_type.spec.is_ordered:
            return self._harville.in_order(shares)
        return self._harville.any_order(shares)
