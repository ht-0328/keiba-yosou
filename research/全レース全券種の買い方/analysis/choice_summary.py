"""セルごとに選んだ型で買ったときの成績（期間・年・セルごと）をまとめる。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .cell_selector import POINT_YEN, CellChoice
from .day_table import HIT_RACES, PAYOUT, POINTS, RACES
from .recovery_bootstrap import RecoveryBootstrap


class ChoiceSummary:
    """候補ごとの集計（配列 [候補, セル, 開催日, 4]）と、セルごとに選んだ候補（``CellChoice``）から、選んだ型で全レースを買ったときの
    成績を出す（docs/01 の 6）。

    - ``selected(values, choices)``: セルごとに選んだ候補の行だけを取り出した配列 [セル, 開催日, 4]。買わないセル（``skip``）は 0。
    - ``summary(selected, day_mask)``: 期間の合計（回収率・90% の幅の下の端・的中率・レース数・1レースの点数・投資・払戻）。
    - ``yearly(selected)``: 年ごとの回収率・的中率・レース数。
    - ``by_cell(selected, cells, day_mask)``: セルごとの成績。
    """

    def __init__(self, days: Sequence[pd.Timestamp]) -> None:
        self._days = pd.DatetimeIndex([pd.Timestamp(day) for day in days])

    @staticmethod
    def selected(values: np.ndarray, choices: Sequence[CellChoice]) -> np.ndarray:
        return np.stack([np.zeros_like(values[0, cell_index]) if choice.skip else values[choice.index, cell_index]
                         for cell_index, choice in enumerate(choices)], axis=0)

    def summary(self, selected: np.ndarray, day_mask: np.ndarray) -> dict[str, float]:
        picked = selected[:, day_mask]                      # [セル, 日, 4]
        per_day = picked.sum(axis=0)                        # [日, 4]
        stake = per_day[:, POINTS].sum() * POINT_YEN
        payout = per_day[:, PAYOUT].sum()
        races = per_day[:, RACES].sum()
        lower = RecoveryBootstrap(int(day_mask.sum())).lower(per_day[:, POINTS] * POINT_YEN, per_day[:, PAYOUT])[0] if stake > 0 else np.nan
        return {"回収率": payout / stake if stake > 0 else np.nan, "下の端": float(lower), "的中率": per_day[:, HIT_RACES].sum() / races if races > 0 else np.nan,
                "レース": float(races), "1レースの点数": per_day[:, POINTS].sum() / races if races > 0 else np.nan, "投資": stake, "払戻": payout}

    def yearly(self, selected: np.ndarray) -> pd.DataFrame:
        rows = []
        for year in sorted(set(self._days.year)):
            summary = self.summary(selected, np.asarray(self._days.year == year))
            rows.append({"年": year, **summary})
        return pd.DataFrame(rows)

    def by_cell(self, selected: np.ndarray, cells: Sequence[str], choices: Sequence[CellChoice], day_mask: np.ndarray) -> pd.DataFrame:
        rows = []
        for cell_index, cell in enumerate(cells):
            one = selected[cell_index][np.newaxis, :, :]
            summary = self.summary(one, day_mask)
            rows.append({"セル": cell, "型": choices[cell_index].label, **summary})
        return pd.DataFrame(rows)

    @staticmethod
    def passes(summary: dict[str, float], yearly: pd.DataFrame, years_needed: int = 5) -> tuple[bool, str]:
        """採用の基準（docs/01 の 6）を満たすか。理由の文も返す。"""
        over_years = int((yearly["回収率"] > 1.0).sum())
        first = summary["回収率"] > 1.0 and summary["下の端"] > 1.0
        second = over_years >= years_needed
        reason = (f"回収率 {'超え' if summary['回収率'] > 1.0 else '届かず'}・下の端 {'超え' if summary['下の端'] > 1.0 else '届かず'}・"
                  f"100% 超えの年 {over_years}/{len(yearly)}")
        return bool(first and second), reason
