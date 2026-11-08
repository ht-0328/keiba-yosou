"""事例の研究の流れ（段1・段2）: 元DB とほかの置き場所を読み、出走の表に列を足し、事例を数え・選び、reports/ に書く。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通 import render
from 共通.render import Table

from .case_sections import CaseSections
from .enrichment.runner_enrichment import RunnerEnrichment, SideTables
from .repository import (DEFAULT_PACE_FORECASTS, DEFAULT_REVIEW_DB, DisadvantageNoteRepository, PaceForecastStore,
                         PreClosePopularityRepository, RaceReviewRepository, RunnerFactsRepository)
from .tables.case_detail_table import CaseDetailTable
from .tables.case_selection import CaseSelection
from .tables.case_summary_table import CaseSummaryTable
from .tables.race_cuts import CUTS
from .theory.race_table import MULTI, WIN_ONLY, RaceTable
from .theory.runner_cuts import RunnerCuts

#: 書くファイルの名前。
REPORT_NAME = "事例"
CASES_CSV = "事例の一覧.csv"
COURSE_CSV = "コースの単位ごとの数.csv"
RUNNERS_CACHE = "出走の表.pkl.gz"
#: 1レースずつ見る事例の数（決着 → 全部の数, そのうちハンデ戦の数）。
CASE_COUNTS: dict[str, tuple[int, int]] = {MULTI: (45, 15), WIN_ONLY: (30, 10)}


@dataclass(frozen=True)
class CaseStudySettings:
    """事例の集め方。``history_from`` は過去走（斤量・位置の近走）をたどるために読み始める日。``odds_from`` は締め切り前の人気を読み始める日。"""

    date_from: date = date(2015, 1, 1)
    history_from: date = date(2012, 1, 1)
    odds_from: date = date(2025, 1, 1)
    review_db: Path = DEFAULT_REVIEW_DB
    pace_forecasts: Path = DEFAULT_PACE_FORECASTS
    case_counts: dict[str, tuple[int, int]] = field(default_factory=lambda: dict(CASE_COUNTS))


@dataclass(frozen=True)
class CaseStudy:
    """``load`` が出走の表を作り（元DB を読む）、``write`` が表・事例の一覧・CSV を ``out_dir`` に書いて Markdown の場所を返す。"""

    settings: CaseStudySettings = CaseStudySettings()

    def load(self, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        s = self.settings
        history = RunnerFactsRepository(con).load(s.history_from)
        store = PaceForecastStore(s.pace_forecasts)
        side = SideTables(reviews=RaceReviewRepository(s.review_db).load(), race_forecasts=store.races(),
                          horse_forecasts=store.horses(), pre_close=PreClosePopularityRepository(con).load(s.odds_from))
        return RunnerEnrichment(s.date_from).build(history, side)

    def write(self, runners: pd.DataFrame, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        runners = RunnerCuts().add(runners)
        races = RaceTable().build(runners)
        sections = CaseSections(runners, races).build()
        chosen = {outcome: CaseSelection().pick(races, outcome, count, handicap)
                  for outcome, (count, handicap) in self.settings.case_counts.items()}
        sections.append(("9. 1レースずつ見た事例", self._case_tables(runners, races, chosen, out_dir)))
        course = CUTS["コースの単位（競馬場・コース・距離・馬場状態）"](races)
        counts = races.assign(course_unit=course).groupby("course_unit").agg(
            races=("longshot_won", "size"), longshot_won=("longshot_won", "sum"), longshot_multi=("longshot_multi", "sum"),
            longshot_all=("longshot_all", "sum"))
        counts.to_csv(out_dir / COURSE_CSV, encoding="utf-8-sig")
        return self._report(out_dir, sections)

    def _case_tables(self, runners: pd.DataFrame, races: pd.DataFrame, chosen: dict[str, list[str]], out_dir: Path) -> list[Table]:
        notes = DisadvantageNoteRepository(self.settings.review_db).load()
        detail = CaseDetailTable()
        ordered = [race_id for ids in chosen.values() for race_id in ids]
        frame = detail.frame(runners, races, ordered, notes)
        frame.to_csv(out_dir / CASES_CSV, index=False, encoding="utf-8-sig")
        summary = CaseSummaryTable().build(runners, chosen, "選んだ事例の来た大穴を数えた結果")
        return [summary, detail.table(frame, f"選んだ事例（来た大穴と1番人気。同じものが {CASES_CSV}）")]

    def _report(self, out_dir: Path, sections: list[tuple[str, list[Table]]]) -> Path:
        s = self.settings
        intro = (f"{s.date_from.isoformat()} 以降の中央の平地のレース。大穴 = 確定の単勝人気が10番人気以下。結果側の列（着順・通過順・上がり・"
                 "ペース・その日の傾き）は、何が起きたかを理解するためだけに使う。予想のペースと位置の見込みは、予想「展開から着順を予想」の"
                 "前日の時点の年ごとの予測（その年より前だけで学んだもの。2016年から）。研究の文書は research/超荒れの展開と適性から大穴を当てる/docs/。")
        parts = ["# 超荒れの展開と適性から大穴を当てる: 事例", intro]
        for section, tables in sections:
            parts.append(f"## {section}")
            parts.extend(render.to_markdown(table) for table in tables)
        path = out_dir / f"{REPORT_NAME}.md"
        path.write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
        return path
