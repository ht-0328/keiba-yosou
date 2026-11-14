"""期間（年や、いくつかの年をまとめたもの）× 等級の ◎ の単勝・複勝の成績と、等級の順に上がったかの判定。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

import pandas as pd

from yosou.shared.race_grade import GRADES

from 共通.perf import percent
from 共通.render import Table

from 地方の期待度.analysis.grade_year_table import GRADE, RATES

_FINISH, _WIN_PAYOUT, _PLACE_PAYOUT = "finish", "win_payout", "place_payout"
_STAKE = 100.0


class GradePeriodTable:
    """``graded`` は ◎ の行（列 ``grade``・``finish``・``win_payout``・``place_payout``）。
    ``rates`` は等級ごとの4つの率（勝率・複勝率・単勝回収率・複勝回収率）、``monotone`` は率ごとに C → B → A → S の順に真に上がったか、
    ``rows`` は1つの期間の等級ごとの表の行（期間の名前・等級・レース数・割合・4つの率）。"""

    @staticmethod
    def rates(graded: pd.DataFrame) -> dict[str, dict[str, float]]:
        """等級 → 率。レースの無い等級は入らない。"""
        out = {}
        for grade in GRADES:
            part = graded[graded[GRADE] == grade]
            if len(part):
                finish = part[_FINISH].astype(float)
                out[grade] = {"勝率": float((finish == 1).mean()), "複勝率": float((finish <= 3).mean()),
                              "単勝回収率": float(part[_WIN_PAYOUT].sum() / (_STAKE * len(part))),
                              "複勝回収率": float(part[_PLACE_PAYOUT].sum() / (_STAKE * len(part)))}
        return out

    def monotone(self, graded: pd.DataFrame) -> dict[str, bool]:
        """率ごとに、4つの等級がそろっていて C → B → A → S の順に真に上がったか。"""
        rates = self.rates(graded)
        if any(grade not in rates for grade in GRADES):
            return {rate: False for rate in RATES}
        return {rate: all(a < b for a, b in pairwise(rates[grade][rate] for grade in reversed(GRADES))) for rate in RATES}

    def count(self, graded: pd.DataFrame, years: Sequence[int], year_column: str = "year") -> int:
        """``years`` の年ごとに順に上がった率の数を足したもの（最大 4 × 年の数）。"""
        return sum(sum(self.monotone(graded[graded[year_column] == year]).values()) for year in years)

    def rows(self, graded: pd.DataFrame, period: str) -> list[list[str]]:
        rates = self.rates(graded)
        rows = []
        for grade in GRADES:
            part = graded[graded[GRADE] == grade]
            values = rates.get(grade)
            rows.append([period, grade, f"{len(part):,}", percent(len(part) / len(graded)) if len(graded) else "—",
                         *(percent(values[rate]) if values else "—" for rate in RATES)])
        return rows

    def table(self, periods: Sequence[tuple[str, pd.DataFrame]], title: str, note: str = "") -> Table:
        rows = [row for name, graded in periods for row in self.rows(graded, name)]
        return Table(["期間", "期待度", "レース数", "レースの割合", *RATES], rows, title=title, note=note)
