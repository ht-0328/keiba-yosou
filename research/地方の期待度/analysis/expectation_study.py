"""期待度の研究の流れ: ◎ の行を読み、点数の候補ごとに線を決める年で線を決め、年ごとの ◎ の成績と推奨買目の成績を表にして Markdown に書く。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from yosou.shared.feature import PredictionTiming
from yosou.shared.race_grade import RANK_LINES

from 共通 import render
from 共通.render import Table

from .grade_lines import GradeLines
from .grade_year_table import GRADE, RATES, GradeYearTable
from .recommended_tickets import RecommendedTickets
from .score_candidate import CANDIDATES
from .top_picks import YEAR, TopPicks

#: 中央の ◎ランクの線をそのまま当てた参考の行の名前。
JRA_LINES_KEY = "A（中央の線のまま）"


@dataclass(frozen=True)
class ExpectationStudySettings:
    """予測の置き場所・学習済みモデル・時点・線を決める年・結果の置き場所。"""

    predictions: Path
    models: Path
    timing: PredictionTiming
    decide_year: int
    out_dir: Path
    db: Path | None = None
    rebuild: bool = False


class ExpectationStudy:
    """候補ごとに: 線を決める年の点数の分位で線を決め、全部の年に等級を付け、年 × 等級の ◎ の単勝・複勝の成績（表）と、
    線を決めた年を除いた年で4つの率（勝率・複勝率・単勝回収率・複勝回収率）が等級の順に上がった年の数（まとめの表）を出す。
    推奨買目の成績（研究「地方の万馬券」の買い目の CSV があれば）も等級ごとに添える。参考に、中央の ◎ランクの線をそのまま当てた A も出す。"""

    def __init__(self, settings: ExpectationStudySettings, tickets: RecommendedTickets | None = None) -> None:
        self._settings = settings
        self._tickets = tickets or RecommendedTickets()
        self._lines = GradeLines()
        self._years = GradeYearTable()

    def run(self) -> Path:
        s = self._settings
        picks = TopPicks(s.predictions, s.models, s.out_dir / "cache")
        tops = picks.load(s.timing, s.db, s.rebuild).dropna(subset=["win_probability", "win_value"])
        verify_years = sorted(int(year) for year in tops[YEAR].unique() if int(year) != s.decide_year)
        tables: list[Table] = []
        summary: list[list[str]] = []
        for candidate in CANDIDATES:
            scores = candidate.score(tops)
            lines = self._lines.decide(scores[tops[YEAR] == s.decide_year])
            tables += self._evaluate(tops, candidate.key, candidate.formula, scores, lines, verify_years, summary)
            if candidate.key == "A":
                tables += self._evaluate(tops, JRA_LINES_KEY, candidate.formula, scores, dict(RANK_LINES), verify_years, summary)
        summary_table = Table(["候補", "式", "線", *(f"{rate}が順に上がった年" for rate in RATES), "上がった回数"], summary,
                              title=f"0. まとめ（{s.timing.label}。線は {s.decide_year}年の分位で決め、ほかの年で確かめる）",
                              note=f"◎ {len(tops):,} レース（{tops[YEAR].min()}〜{tops[YEAR].max()}年）。「順に上がった」は C → B → A → S の順に率が真に上がったこと。"
                                   f"上がった回数の最大は {len(RATES) * len(verify_years)}（4つの率 × 確かめる年 {len(verify_years)}）。"
                                   f"中央の線は {GradeLines.legend(dict(RANK_LINES))}。")
        path = s.out_dir / f"期待度の候補-{s.timing.label}.md"
        render.write(render.render([summary_table, *tables], "markdown"), path, fmt="markdown")
        print(f"保存先: {path}", file=sys.stderr, flush=True)
        return path

    def _evaluate(self, tops: pd.DataFrame, key: str, formula: str, scores: pd.Series, lines: dict[str, float],
                  verify_years: list[int], summary: list[list[str]]) -> list[Table]:
        graded = tops.assign(**{GRADE: GradeLines.grade(scores, lines)})
        monotone = self._years.monotone_years(graded, verify_years)
        legend = GradeLines.legend(lines)
        summary.append([key, formula, legend, *("・".join(str(year) for year in monotone[rate]) or "—" for rate in RATES),
                        str(sum(len(years) for years in monotone.values()))])
        tables = [self._years.table(graded, f"{key}. {formula}（{legend}）", note="◎ の単勝・複勝を 1点 100円でべた買いしたときの成績。回収率は確定オッズの払戻。")]
        if self._tickets.available():
            tables.append(self._tickets.table(graded, f"{key}. 推奨買目の成績（{legend}）",
                                              note="研究「地方の万馬券」段5 の買い目（単勝〜3連単の8券種。11頭以上・各年を残りの年で当てはめた未見の評価）を、"
                                                   "◎ の期待度の等級ごとにまとめたもの。1点 100円。"))
        return tables
