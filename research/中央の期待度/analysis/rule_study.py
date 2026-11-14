"""◎ の選び方 × 期待度の重みの組を比べ、「どの等級でも ◎ の単勝回収率が 100% を超え、S → C の順に勝率と単勝回収率が上がる」組を探す。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import pandas as pd

from yosou.shared.race_grade import GRADES

from 共通 import render
from 共通.perf import percent
from 共通.render import Table

from 地方の期待度.analysis.grade_lines import GradeLines
from 地方の期待度.analysis.grade_year_table import GRADE

from .grade_period_table import GradePeriodTable
from .top_rules import RULES, TopRule
from .weight_candidates import WEIGHTS, weighted

#: 等級ごとに並べる率。
_WIN_RATE, _WIN_BACK, _PLACE_BACK = "勝率", "単勝回収率", "複勝回収率"


@dataclass(frozen=True)
class PairResult:
    """1つの組（◎ の選び方 × 重み）の結果。``decide``・``verify`` は等級 → 率（決める期間・確かめる期間をまとめたもの）。"""

    rule: TopRule
    weight: float
    lines: dict[str, float]
    all_back: float
    decide: dict[str, dict[str, float]]
    verify: dict[str, dict[str, float]]

    @staticmethod
    def passes(rates: dict[str, dict[str, float]]) -> bool:
        """どの等級でも単勝回収率が 100% を超え、C → S の順に勝率と単勝回収率が真に上がる。"""
        if any(grade not in rates for grade in GRADES):
            return False
        ordered = [rates[grade] for grade in reversed(GRADES)]
        return (all(rate[_WIN_BACK] > 1.0 for rate in ordered)
                and all(a[_WIN_RATE] < b[_WIN_RATE] and a[_WIN_BACK] < b[_WIN_BACK] for a, b in pairwise(ordered)))

    @staticmethod
    def lowest(rates: dict[str, dict[str, float]]) -> float:
        """等級の中でいちばん低い単勝回収率（等級が欠ければ 0）。"""
        return min((rates[grade][_WIN_BACK] for grade in GRADES if grade in rates), default=0.0) if len(rates) == len(GRADES) else 0.0


class RuleStudy:
    """``rows`` は印を付けた全頭の行（列 ``year`` つき）。組ごとに、``decide_years`` の ◎ の点数の分位で線を決め（上から 20%・30%・30%・20%）、
    決める期間と確かめる期間の等級ごとの成績を出す。

    選び方（結果を見る前に決めた決まり）: 決める期間で ``PairResult.passes`` を満たす組のうち、等級の中でいちばん低い単勝回収率が
    いちばん高い組。満たす組が無ければ「無し」とし、いちばん近い組（いちばん低い単勝回収率がいちばん高い組）を参考に出す。
    確かめる期間の結果は選ぶのに使わない。"""

    def __init__(self, rows: pd.DataFrame, decide_years: Sequence[int], rules: Sequence[TopRule] = RULES,
                 weights: Sequence[float] = WEIGHTS) -> None:
        self._rows = rows
        self._decide = sorted(int(year) for year in decide_years)
        self._rules = tuple(rules)
        self._weights = tuple(weights)
        self._lines = GradeLines()
        self._periods = GradePeriodTable()

    def results(self) -> list[PairResult]:
        out = []
        for rule in self._rules:
            tops = rule.tops(self._rows).dropna(subset=["win_probability", "win_value"])
            in_decide = tops["year"].isin(self._decide)
            all_back = float(tops["win_payout"].sum() / (100.0 * len(tops))) if len(tops) else 0.0
            for weight in self._weights:
                scores = weighted(weight).score(tops)
                lines = self._lines.decide(scores[in_decide])
                graded = tops.assign(**{GRADE: GradeLines.grade(scores, lines)})
                out.append(PairResult(rule, weight, lines, all_back, self._periods.rates(graded[in_decide]),
                                      self._periods.rates(graded[~in_decide])))
        return out

    @staticmethod
    def choose(results: Sequence[PairResult]) -> tuple[PairResult | None, PairResult]:
        """（決まりで選んだ組か None, いちばん近い組）。"""
        nearest = max(results, key=lambda result: PairResult.lowest(result.decide))
        passing = [result for result in results if PairResult.passes(result.decide)]
        return (max(passing, key=lambda result: PairResult.lowest(result.decide)) if passing else None), nearest

    def write(self, path: Path) -> Path:
        results = self.results()
        chosen, nearest = self.choose(results)
        rows = []
        for result in sorted(results, key=lambda result: PairResult.lowest(result.decide), reverse=True):
            tag = "（選んだ）" if result is chosen else "（いちばん近い）" if chosen is None and result is nearest else ""
            rows.append([result.rule.key + tag, f"{result.weight:g}", GradeLines.legend(result.lines), percent(result.all_back),
                         self._grades(result.decide, _WIN_BACK), self._grades(result.decide, _WIN_RATE),
                         "満たす" if PairResult.passes(result.decide) else "—",
                         self._grades(result.verify, _WIN_BACK), self._grades(result.verify, _WIN_RATE), self._grades(result.verify, _PLACE_BACK),
                         "満たす" if PairResult.passes(result.verify) else "—"])
        decide = f"{self._decide[0]}〜{self._decide[-1]}年"
        table = Table(["◎ の選び方", "重み", "線", "◎ 全体の単勝回収率", f"{decide} 単勝回収率 S/A/B/C", f"{decide} 勝率 S/A/B/C", f"{decide} 条件",
                       "確かめる期間 単勝回収率 S/A/B/C", "確かめる期間 勝率 S/A/B/C", "確かめる期間 複勝回収率 S/A/B/C", "確かめる期間 条件"], rows,
                      title=f"◎ の選び方 × 期待度の重み（当日。線と選び方は {decide}、確かめる期間はそれ以外の年）",
                      note="条件: どの等級でも ◎ の単勝回収率が 100% を超え、C → S の順に勝率と単勝回収率が真に上がる。"
                           "並びは決める期間の等級の中でいちばん低い単勝回収率の高い順。選び方: 決める期間で条件を満たす組のうち、その値がいちばん高い組"
                           "（確かめる期間の結果は選ぶのに使っていない）。◎ の選び方: "
                           + "。".join(f"{rule.key} = {rule.label}" for rule in self._rules) + "。")
        path.parent.mkdir(parents=True, exist_ok=True)
        render.write(render.render([table], "markdown"), path, fmt="markdown")
        print(f"保存先: {path}", file=sys.stderr, flush=True)
        if chosen is None:
            print(f"決める期間で条件を満たす組はありません。いちばん近い組: {nearest.rule.key} × 重み {nearest.weight:g}", file=sys.stderr, flush=True)
        else:
            print(f"選んだ組: {chosen.rule.key} × 重み {chosen.weight:g}（確かめる期間: {'満たす' if PairResult.passes(chosen.verify) else '満たさない'}）",
                  file=sys.stderr, flush=True)
        return path

    @staticmethod
    def _grades(rates: dict[str, dict[str, float]], name: str) -> str:
        return " / ".join(f"{rates[grade][name] * 100:.0f}" if grade in rates else "—" for grade in GRADES)
