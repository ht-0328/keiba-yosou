"""中央の期待度の重みの研究の流れ: 重みの候補ごとに、決める期間で線を決め、決める期間・確かめる期間・年ごとの ◎ の成績を表にし、決まりで重みを1つ選ぶ。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from yosou.shared.race_grade import RANK_LINES

from 共通 import render
from 共通.render import Table

from 地方の期待度.analysis.grade_lines import GradeLines
from 地方の期待度.analysis.grade_year_table import GRADE, RATES
from 地方の期待度.analysis.score_candidate import ScoreCandidate
from 地方の期待度.analysis.top_picks import YEAR

from .grade_period_table import GradePeriodTable
from .weight_candidates import CANDIDATES

#: 今の本番（重み 1・今の線）の参考の行の名前。
CURRENT_KEY = "今の本番（重み 1・今の線）"


@dataclass(frozen=True)
class CandidateResult:
    """1つの候補の結果。``decide_all`` は決める期間をまとめて4つの率が全部順に上がったか、``decide_years`` は決める期間の年ごとに
    順に上がった率の数の合計、``verify_all`` は確かめる期間をまとめて4つの率が全部順に上がったか、``verify_years`` は確かめる期間の年ごとの合計。"""

    key: str
    formula: str
    lines: dict[str, float]
    decide_monotone: dict[str, bool]
    decide_years: int
    verify_monotone: dict[str, bool]
    verify_years: int

    @property
    def decide_all(self) -> bool:
        return all(self.decide_monotone.values())

    @property
    def verify_all(self) -> bool:
        return all(self.verify_monotone.values())


class WeightStudy:
    """``tops`` は ◎ の行（``JraTopPicks``）。``decide_years`` で線を決め（分位。上から 20%・30%・30%・20%）、残りの年で確かめる。

    重みの選び方（結果を見る前に決めた決まり）: 決める期間をまとめて4つの率（勝率・複勝率・単勝回収率・複勝回収率）が全部 C → B → A → S の順に
    上がる候補のうち、決める期間の年ごとに順に上がった率の数がいちばん多いもの。同じなら重みの小さいもの（今の式に近いもの）。
    確かめる期間の結果は選ぶのに使わない（選んだ候補が確かめる期間でも順に上がるかを1回だけ見る）。"""

    def __init__(self, tops: pd.DataFrame, decide_years: Sequence[int], candidates: Sequence[ScoreCandidate] = CANDIDATES) -> None:
        self._tops = tops.dropna(subset=["win_probability", "win_value"]).reset_index(drop=True)
        self._decide_years = sorted(int(year) for year in decide_years)
        self._verify_years = sorted(int(year) for year in self._tops[YEAR].unique() if int(year) not in self._decide_years)
        self._candidates = tuple(candidates)
        self._lines = GradeLines()
        self._periods = GradePeriodTable()

    def results(self) -> list[CandidateResult]:
        decide = self._tops[YEAR].isin(self._decide_years)
        out = []
        for candidate in self._candidates:
            scores = candidate.score(self._tops)
            out.append(self._result(candidate.key, candidate.formula, scores, self._lines.decide(scores[decide])))
        first = self._candidates[0]
        out.append(self._result(CURRENT_KEY, first.formula, first.score(self._tops), dict(RANK_LINES)))
        return out

    @staticmethod
    def choose(results: Sequence[CandidateResult]) -> CandidateResult | None:
        """決まりで選んだ候補（今の本番の参考の行は選ばない）。決める期間で順に上がる候補が無ければ None。"""
        eligible = [result for result in results if result.key != CURRENT_KEY and result.decide_all]
        if not eligible:
            return None
        best = max(result.decide_years for result in eligible)
        return next(result for result in eligible if result.decide_years == best)   # 候補は重みの小さい順に並んでいる

    def write(self, path: Path) -> Path:
        results = self.results()
        chosen = self.choose(results)
        tables = [self._summary(results, chosen)]
        for result in results:
            tables.append(self._detail(result))
        path.parent.mkdir(parents=True, exist_ok=True)
        render.write(render.render(tables, "markdown"), path, fmt="markdown")
        print(f"保存先: {path}", file=sys.stderr, flush=True)
        return path

    def graded(self, lines: dict[str, float], scores: pd.Series) -> pd.DataFrame:
        return self._tops.assign(**{GRADE: GradeLines.grade(scores, lines)})

    def _result(self, key: str, formula: str, scores: pd.Series, lines: dict[str, float]) -> CandidateResult:
        graded = self.graded(lines, scores)
        decide = graded[graded[YEAR].isin(self._decide_years)]
        verify = graded[graded[YEAR].isin(self._verify_years)]
        return CandidateResult(key, formula, lines, self._periods.monotone(decide), self._periods.count(graded, self._decide_years),
                               self._periods.monotone(verify), self._periods.count(graded, self._verify_years))

    def _summary(self, results: Sequence[CandidateResult], chosen: CandidateResult | None) -> Table:
        def marks(monotone: dict[str, bool]) -> str:
            return "・".join(rate for rate in RATES if monotone[rate]) or "—"

        rows = [[result.key + ("（選んだ）" if chosen is not None and result.key == chosen.key else ""), result.formula,
                 GradeLines.legend(result.lines), marks(result.decide_monotone), f"{result.decide_years} / {4 * len(self._decide_years)}",
                 marks(result.verify_monotone), f"{result.verify_years} / {4 * len(self._verify_years)}"] for result in results]
        decide, verify = self._label(self._decide_years), self._label(self._verify_years)
        return Table(["候補", "式", "線", f"{decide}で順に上がった率", f"{decide}の年ごとの数", f"{verify}で順に上がった率", f"{verify}の年ごとの数"], rows,
                     title=f"0. まとめ（当日。線は {decide}の分位で決め、{verify}で確かめる）",
                     note=f"◎ {len(self._tops):,} レース（{self._tops[YEAR].min()}〜{self._tops[YEAR].max()}年。7つの区切りのテスト期間）。"
                          "「順に上がった」は C → B → A → S の順に率が真に上がったこと。年ごとの数は、年ごとに順に上がった率の数の合計（最大 4 × 年の数）。"
                          "選び方: 決める期間をまとめて4つの率が全部順に上がる候補のうち、決める期間の年ごとの数がいちばん多いもの（同じなら重みの小さいもの）。"
                          "確かめる期間の結果は選ぶのに使っていない。")

    def _detail(self, result: CandidateResult) -> Table:
        scores = next((candidate.score(self._tops) for candidate in self._candidates if candidate.formula == result.formula), None)
        graded = self.graded(result.lines, scores)
        periods = [(f"{self._label(self._decide_years)}（決める）", graded[graded[YEAR].isin(self._decide_years)]),
                   (f"{self._label(self._verify_years)}（確かめる）", graded[graded[YEAR].isin(self._verify_years)]),
                   *((str(year), graded[graded[YEAR] == year]) for year in sorted(graded[YEAR].unique()))]
        return self._periods.table(periods, f"{result.key}. {result.formula}（{GradeLines.legend(result.lines)}）",
                                   note="◎ の単勝・複勝を 1点 100円でべた買いしたときの成績。回収率は確定オッズの払戻。")

    @staticmethod
    def _label(years: Sequence[int]) -> str:
        if not years:
            return "—"
        return f"{years[0]}年" if len(years) == 1 else f"{years[0]}〜{years[-1]}年"
