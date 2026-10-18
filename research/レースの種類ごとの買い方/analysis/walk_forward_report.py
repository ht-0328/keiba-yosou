"""ウォークフォワードの成績を数え、採用の基準（docs/01 の 6）に照らす。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval

from .profit_bootstrap import ProfitBootstrap
from .rule_day_table import HIT_RACES, PAYOUT, POINTS, RACES

#: 数える年と、前半・後半（docs/01 の 5・6）。
TEST_YEARS: tuple[int, ...] = tuple(range(2018, 2027))
HALVES: tuple[tuple[int, int], ...] = ((2018, 2021), (2022, 2026))
#: 回収率が 100% を超えた年が、この数以上あること（基準 4）。
MIN_GOOD_YEARS = 5


@dataclass(frozen=True)
class Summary:
    """1つの案の、数える年の成績。回収率・的中率は割合（1.0 = 100%）。利益の下の端は円。"""

    name: str
    races: int
    points: int
    hit_races: int
    hit_rate: float
    payback: float
    low: float
    high: float
    lower_profit: float
    halves: tuple[float, ...]
    yearly: dict[int, float]

    @property
    def good_years(self) -> int:
        return sum(1 for value in self.yearly.values() if value > 1.0)


class WalkForwardReport:
    """開催日ごとの成績 [開催日, 4]（``WalkForwardSelector`` か ``CurrentTickets`` の形）から、数える年の成績（``Summary``）を出し、
    今の本番と比べて採用の基準の4つを満たすかを判定する。"""

    def __init__(self, days: Sequence[pd.Timestamp]) -> None:
        self._days = pd.DatetimeIndex(days)
        self._years = self._days.year.to_numpy()

    def summary(self, name: str, daily: np.ndarray) -> Summary:
        inside = np.isin(self._years, TEST_YEARS)
        cells = daily[inside]
        points, payout = cells[:, POINTS].sum(), cells[:, PAYOUT].sum()
        races, hits = cells[:, RACES].sum(), cells[:, HIT_RACES].sum()
        bought = cells[:, POINTS] > 0
        low, high = BootstrapInterval().of(pd.Series(self._days[inside][bought]), pd.Series(100.0 * cells[bought, POINTS]),
                                           pd.Series(cells[bought, PAYOUT]))
        profit = (cells[:, PAYOUT] - 100.0 * cells[:, POINTS])[:, None]
        lower_profit = float(ProfitBootstrap(len(cells)).lower(profit)[0])
        return Summary(name, int(races), int(points), int(hits), self._ratio(hits, races), self._ratio(payout, 100.0 * points),
                       low, high, lower_profit, tuple(self._payback(daily, first, last) for first, last in HALVES),
                       {year: self._payback(daily, year, year) for year in TEST_YEARS})

    def verdict(self, candidate: Summary, current: Summary) -> tuple[bool, bool, bool, bool]:
        """採用の基準 1〜4 を満たすか（docs/01 の 6）。"""
        first = candidate.payback > 1.0 and candidate.low > 1.0
        second = (candidate.payback >= current.payback and candidate.races >= current.races and candidate.hit_rate >= current.hit_rate)
        third = all(new >= old for new, old in zip(candidate.halves, current.halves) if not np.isnan(old))
        return first, second, third, candidate.good_years >= MIN_GOOD_YEARS

    def table(self, summaries: Sequence[Summary], current: Summary, references: Sequence[str] = ()) -> pd.DataFrame:
        """``references`` は比べるための行の名前（採用の候補にしない。今の本番そのものや数え方の確かめ）。"""
        rows = []
        for item in summaries:
            marks = self.verdict(item, current)
            candidate = all(marks) and item.name not in references and item is not current
            rows.append({"案": item.name, "レース": item.races, "点数": item.points, "当たったレース": item.hit_races,
                         "的中率(レース)%": round(100 * item.hit_rate, 2), "回収率%": round(100 * item.payback, 1),
                         "90%の幅": f"{100 * item.low:.1f}〜{100 * item.high:.1f}", "利益の下の端(円)": round(item.lower_profit),
                         "前半%": round(100 * item.halves[0], 1), "後半%": round(100 * item.halves[1], 1),
                         "100%超えの年": item.good_years, "基準1〜4": "".join("○" if mark else "×" for mark in marks),
                         "候補": "◎" if candidate else ""})
        return pd.DataFrame(rows)

    def yearly(self, summaries: Sequence[Summary]) -> pd.DataFrame:
        return pd.DataFrame({item.name: {year: round(100 * value, 1) for year, value in item.yearly.items()} for item in summaries}).T

    def _payback(self, daily: np.ndarray, first: int, last: int) -> float:
        cells = daily[(self._years >= first) & (self._years <= last)]
        return self._ratio(cells[:, PAYOUT].sum(), 100.0 * cells[:, POINTS].sum())

    @staticmethod
    def _ratio(top: float, bottom: float) -> float:
        return float(top / bottom) if bottom > 0 else float("nan")
