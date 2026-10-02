"""期待値の線を、直前の1年で選ぶ。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from . import columns as c
from .candidate_picker import CandidatePicker
from .protocol import LINE_CANDIDATES, MIN_LINE_RETURN_RATE

#: 線ごとの表の列。
LINE_COLUMN, POINTS, STAKE, PAYOUT, RATE, ELIGIBLE = "線", "点数", "賭け金（円）", "払戻（円）", "回収率", "条件に合う"


class ValidationLineChooser:
    """直前の1年の枠A（全レース・1レース最大3点）で、回収率が ``min_return_rate`` を超え、``min_points`` 点以上残る線のうち、
    回収率がいちばん高い線を選ぶ（docs/05-round3-protocol.md の「線の選び方」）。条件に合う線が無ければ NaN（その区切りは買わない）。

    候補は研究「回収率100超」と同じ 1.00〜1.40。テスト期間の行は渡さない（呼ぶ側が直前の1年だけを渡す）。
    """

    def __init__(self, picker: CandidatePicker, candidates: Sequence[float] = LINE_CANDIDATES,
                 min_return_rate: float = MIN_LINE_RETURN_RATE) -> None:
        self._picker = picker
        self._candidates = tuple(candidates)
        self._min_return_rate = min_return_rate

    def table(self, valued_history: pd.DataFrame, min_points: int) -> pd.DataFrame:
        """線ごとの点数・賭け金・払戻・回収率と、条件に合うか。"""
        rows = [self._row(valued_history, line, min_points) for line in self._candidates]
        return pd.DataFrame(rows, columns=[LINE_COLUMN, POINTS, STAKE, PAYOUT, RATE, ELIGIBLE])

    def choose(self, valued_history: pd.DataFrame, min_points: int) -> float:
        table = self.table(valued_history, min_points)
        eligible = table[table[ELIGIBLE]]
        if eligible.empty:
            return float("nan")
        return float(eligible.sort_values([RATE, LINE_COLUMN], ascending=[False, True]).iloc[0][LINE_COLUMN])

    def _row(self, valued_history: pd.DataFrame, line: float, min_points: int) -> list[object]:
        tickets = self._picker.pick(valued_history, line)
        stake, payout = int(tickets[c.STAKE_YEN].sum()), int(tickets[c.PAYOUT_YEN].sum())
        rate = payout / stake if stake else np.nan
        eligible = bool(len(tickets) >= min_points and stake > 0 and rate > self._min_return_rate)
        return [line, len(tickets), stake, payout, rate, eligible]
