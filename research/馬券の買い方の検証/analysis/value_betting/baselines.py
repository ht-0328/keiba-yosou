"""比べる目安（全穴馬の複勝・1番人気の複勝・全頭の複勝）。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pandas as pd

from . import columns as c
from .materials import Round3Materials
from .protocol import STAKE_YEN
from .ticket_summary import TicketSummary

#: 目安の名前 → 対象の行の選び方。どれも 1点 100円、全レース。
BASELINES: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "全穴馬の複勝": lambda rows: rows[c.LONGSHOT_ZONE].notna(),
    "1番人気の複勝": lambda rows: rows[c.POPULARITY] == 1,
    "全頭の複勝": lambda rows: pd.Series(True, index=rows.index),
}
_PAYOUT_PER_YEN = 100.0


class BaselineBets:
    """段階の区切りのテスト期間で、目安の買い方（``BASELINES``）をしたときの買い目とまとめを出す。
    期待値や線は使わず、対象の馬を全部 100円ずつ買う。"""

    def __init__(self, materials: Round3Materials, stake_yen: int = STAKE_YEN) -> None:
        self._materials = materials
        self._stake_yen = stake_yen

    def tickets(self, name: str, window_names: Sequence[str]) -> pd.DataFrame:
        rows = pd.concat([self._materials.runners_of(window, c.PART_TEST) for window in window_names], ignore_index=True)
        chosen = rows[BASELINES[name](rows)]
        payout = chosen[c.PLACE_PAYOUT].fillna(0.0).astype(float) * self._stake_yen / _PAYOUT_PER_YEN
        return chosen.assign(**{c.STAKE_YEN: self._stake_yen, c.PAYOUT_YEN: payout.round().astype(int)}).reset_index(drop=True)

    def summaries(self, window_names: Sequence[str]) -> dict[str, TicketSummary]:
        """目安の名前 → まとめ。"""
        return {name: TicketSummary.of(self.tickets(name, window_names)) for name in BASELINES}
