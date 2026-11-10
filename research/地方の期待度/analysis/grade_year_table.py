"""年 × 等級の ◎ の単勝・複勝の成績の表と、等級の順に上がったかの数え上げ。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

import pandas as pd

from yosou.shared.race_grade import GRADES

from 共通.perf import percent
from 共通.render import Table

#: 等級の列。
GRADE = "grade"
#: 等級の順に上がるかを見る4つの率。
RATES: tuple[str, ...] = ("勝率", "複勝率", "単勝回収率", "複勝回収率")
_YEAR, _FINISH, _WIN_PAYOUT, _PLACE_PAYOUT = "year", "finish", "win_payout", "place_payout"
_STAKE = 100.0


class GradeYearTable:
    """``graded`` は ◎ の行（列 ``year``・``grade``・``finish``・``win_payout``・``place_payout``）。
    ``table`` は年ごとに等級の行（レース数・割合・勝率・複勝率・単勝回収率・複勝回収率）を並べる。
    ``monotone_years`` は、率ごとに「C → B → A → S の順に真に上がった年」を数える（``years`` を渡せばその年だけ。線を決めた年は外して数える）。"""

    def table(self, graded: pd.DataFrame, title: str, note: str = "") -> Table:
        rows = []
        for year, part in graded.groupby(_YEAR, sort=True):
            for grade in GRADES:
                rows.append([str(year), grade, *self._cells(part[part[GRADE] == grade], len(part))])
            rows.append([str(year), "全体", *self._cells(part, len(part))])
        return Table(["年", "期待度", "レース数", "レースの割合", *RATES], rows, title=title, note=note)

    def rates(self, graded: pd.DataFrame) -> dict[tuple[int, str], dict[str, float]]:
        """（年, 等級）→ 率。レースの無い等級は入らない。"""
        out = {}
        for (year, grade), part in graded.groupby([_YEAR, GRADE], sort=True):
            if len(part):
                out[(int(year), str(grade))] = self._rates(part)
        return out

    def monotone_years(self, graded: pd.DataFrame, years: Sequence[int] | None = None) -> dict[str, list[int]]:
        rates = self.rates(graded)
        chosen = sorted({year for year, _ in rates} if years is None else set(years))
        result: dict[str, list[int]] = {rate: [] for rate in RATES}
        for year in chosen:
            if any((year, grade) not in rates for grade in GRADES):
                continue
            for rate in RATES:
                values = [rates[(year, grade)][rate] for grade in reversed(GRADES)]
                if all(a < b for a, b in pairwise(values)):
                    result[rate].append(year)
        return result

    @staticmethod
    def _rates(part: pd.DataFrame) -> dict[str, float]:
        n = len(part)
        finish = part[_FINISH].astype(float)
        return {"勝率": float((finish == 1).mean()), "複勝率": float((finish <= 3).mean()),
                "単勝回収率": float(part[_WIN_PAYOUT].sum() / (_STAKE * n)), "複勝回収率": float(part[_PLACE_PAYOUT].sum() / (_STAKE * n))}

    def _cells(self, part: pd.DataFrame, total: int) -> list[str]:
        if part.empty:
            return ["0", percent(0.0), *["—"] * len(RATES)]
        rates = self._rates(part)
        return [f"{len(part):,}", percent(len(part) / total), *(percent(rates[rate]) for rate in RATES)]
