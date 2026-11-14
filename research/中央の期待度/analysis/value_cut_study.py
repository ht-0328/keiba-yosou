"""◎ の単勝の期待値が線以上のレースだけに等級を付け、線・重み・等級の割合を変えて、全等級で ◎ の単勝回収率が 100% を超える組を探す。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise, product
from pathlib import Path

import numpy as np
import pandas as pd

from yosou.shared.race_grade import GRADES, RANK_LINES, RANK_VALUE_WEIGHT, SKIP_GRADE, SKIP_VALUE, TopRankScale

from 共通 import render
from 共通.render import Table

#: 調べる値。
CUTS: tuple[float, ...] = (0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975, 1.0)
WEIGHTS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
SHARES: tuple[tuple[float, float, float], ...] = ((0.2, 0.3, 0.3), (0.25, 0.25, 0.25), (0.15, 0.25, 0.3), (0.1, 0.3, 0.3), (0.3, 0.3, 0.2), (0.1, 0.2, 0.3))
#: 率の並び（勝率, 単勝回収率, 複勝回収率, レース数）。
Rates = dict[str, tuple[float, float, float, int]]


def rates_of(part: pd.DataFrame, grades: np.ndarray) -> Rates:
    out = {}
    for grade in (*GRADES, SKIP_GRADE):
        chosen = part[grades == grade]
        if len(chosen):
            out[grade] = (float((chosen["finish"] == 1).mean()), float(chosen["win_payout"].sum() / (100.0 * len(chosen))),
                          float(chosen["place_payout"].sum() / (100.0 * len(chosen))), int(len(chosen)))
    return out


def meets(rates: Rates) -> bool:
    """S・A・B・C のどれも単勝回収率が 100% を超え、C → S の順に勝率が真に上がる。"""
    if any(grade not in rates for grade in GRADES):
        return False
    ordered = [rates[grade] for grade in reversed(GRADES)]
    return all(rate[1] > 1.0 for rate in ordered) and all(a[0] < b[0] for a, b in pairwise(ordered))


@dataclass(frozen=True)
class CutResult:
    cut: float
    weight: float
    shares: tuple[float, float, float]
    covered: float
    search: Rates
    check: Rates


class ValueCutStudy:
    """``tops`` は ◎ の行（``JraTopPicks``）。``search_years`` の年で線（点数の分位）を決め、残りの年で確かめる。
    ``results`` は線・重み・割合の全部の組、``production`` は本番の決まり（``TopRankScale.grade``）で年ごとの等級別の成績。"""

    def __init__(self, tops: pd.DataFrame, search_years: Sequence[int]) -> None:
        self._tops = tops.dropna(subset=["win_probability", "win_value"]).reset_index(drop=True)
        self._search = self._tops["year"].isin(list(search_years)).to_numpy()

    def results(self) -> list[CutResult]:
        out = []
        value = self._tops["win_value"].astype(float).to_numpy()
        probability = self._tops["win_probability"].astype(float).to_numpy()
        for cut, weight, shares in product(CUTS, WEIGHTS, SHARES):
            kept = value >= cut
            score = probability + weight * (value - 1.0)
            s, a, b = shares
            in_search = kept & self._search
            lines = [float(np.quantile(score[in_search], q)) for q in (1 - s, 1 - s - a, 1 - s - a - b)]
            grades = np.where(~kept, SKIP_GRADE, np.select([score >= lines[0], score >= lines[1], score >= lines[2]], ["S", "A", "B"], "C"))
            out.append(CutResult(cut, weight, shares, float(kept.mean()), rates_of(self._tops[self._search], grades[self._search]),
                                 rates_of(self._tops[~self._search], grades[~self._search])))
        return out

    def production(self) -> pd.DataFrame:
        scale = TopRankScale()
        grades = np.array([scale.grade(p, v) for p, v in zip(self._tops["win_probability"], self._tops["win_value"], strict=True)], dtype=object)
        rows = []
        for name, mask in [("探す期間", self._search), ("確かめる期間", ~self._search),
                           *((str(year), (self._tops["year"] == year).to_numpy()) for year in sorted(self._tops["year"].unique()))]:
            for grade, (win, back, place, count) in rates_of(self._tops[mask], grades[mask]).items():
                rows.append([name, grade, f"{count:,}", f"{count / mask.sum():.1%}", f"{win:.1%}", f"{back:.1%}", f"{place:.1%}"])
        return pd.DataFrame(rows, columns=["期間", "期待度", "レース数", "レースの割合", "勝率", "単勝回収率", "複勝回収率"])

    def write(self, path: Path) -> Path:
        results = self.results()
        both = [result for result in results if meets(result.search) and meets(result.check)]
        rows = [[f"{result.cut:g}", f"{result.weight:g}", "・".join(f"{share:.0%}" for share in result.shares), f"{result.covered:.1%}",
                 _cells(result.search), _cells(result.check), "満たす" if meets(result.search) else "—", "満たす" if meets(result.check) else "—"]
                for result in sorted(results, key=lambda result: (-(meets(result.search) and meets(result.check)), -result.covered, -_lowest(result.search)))]
        table = Table(["見送りの線", "重み", "S・A・B の割合", "等級を付けたレース", "探す期間 単勝回収率/勝率", "確かめる期間 単勝回収率/勝率", "探す期間", "確かめる期間"],
                      rows, title="1. 見送りの線 × 重み × 等級の割合",
                      note="条件: S・A・B・C のどれも ◎ の単勝回収率が 100% を超え、C → S の順に勝率が上がる。"
                           f"両方の期間で満たした組は {len(both)}。並びは両方で満たした組を先に、等級を付けたレースの多い順。")
        legend = (f"本番の決まり: ◎ の単勝の期待値 {SKIP_VALUE:.2f} 未満は{SKIP_GRADE}、それ以外は 1着の確率 ＋ {RANK_VALUE_WEIGHT:g} ×（期待値 − 1）を "
                  f"S {RANK_LINES['S']:g}・A {RANK_LINES['A']:g}・B {RANK_LINES['B']:g} の線で")
        production = self.production()
        production_table = Table(list(production.columns), production.astype(str).values.tolist(), title="2. 本番の決まりの期間・年ごとの成績", note=legend)
        path.parent.mkdir(parents=True, exist_ok=True)
        render.write(render.render([production_table, table], "markdown"), path, fmt="markdown")
        print(f"保存先: {path}", file=sys.stderr, flush=True)
        return path


def _cells(rates: Rates) -> str:
    return " ".join(f"{grade}{rates[grade][1] * 100:.0f}/{rates[grade][0] * 100:.0f}" for grade in GRADES if grade in rates)


def _lowest(rates: Rates) -> float:
    return min((rates[grade][1] for grade in GRADES if grade in rates), default=0.0)
