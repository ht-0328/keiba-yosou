"""理論の研究の流れ（段2）: ファイナルレースの出走馬の表を作り、理論の区分ごとに同じ人気の馬と比べた表を書く。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table
from 地方の万馬券.analysis.case_report import CaseReport

from .period_split import PeriodSplit
from .popularity_band import PopularityBand
from .runner_tables import RunnerTables
from .theory_catalog import GROUPS, THEORIES
from .theory_check_table import TheoryCheckTable

REPORT_NAME = "理論の検証"
#: 書く CSV。
THEORY_CSV = "理論の検証.csv"


@dataclass(frozen=True)
class TheoryStudySettings:
    """理論の確かめ方。"""

    min_heads: int = 9
    popularity: PopularityBand = PopularityBand()
    periods: PeriodSplit = PeriodSplit()
    min_runs: int = 60
    min_period_runs: int = 20


@dataclass(frozen=True)
class TheoryStudy:
    """元DB（地方）から理論の検証の表を作る。``run`` が表を書き、書いた場所を返す。"""

    con: duckdb.DuckDBPyConnection
    settings: TheoryStudySettings = TheoryStudySettings()

    def run(self, out_dir: Path) -> Path:
        s = self.settings
        _, runners = RunnerTables(self.con, s.min_heads, s.popularity).load()
        checker = TheoryCheckTable(s.periods, s.min_runs, s.min_period_runs)
        tables = [checker.build(runners, tuple(theory for theory in THEORIES if theory.group == group), title=group)
                  for group in GROUPS]
        self._write_csv(out_dir, tables)
        return CaseReport(out_dir).write(REPORT_NAME, "高知ファイナルの高配当: 理論の検証", self._intro(runners), tables)

    def _intro(self, runners: pd.DataFrame) -> str:
        s = self.settings
        days = pd.to_datetime(runners["race_date"])
        return (f"対象: 高知のファイナルレース（その日の最終レース）のうち {s.min_heads}頭以上の {runners['race_id'].nunique():,} レース、"
                f"出走 {len(runners):,} 頭（{days.min():%Y-%m-%d} 〜 {days.max():%Y-%m-%d}）。人気の帯は {s.popularity.label}。\n\n"
                f"基準（全部の馬を買ったとき）: 単勝回収率 {runners['win_return'].mean():.1%}・複勝回収率 {runners['place_return'].mean():.1%}。"
                "材料はレースの前に分かるものだけ（過去走は高知の出走、騎手はその日より前の 365日、その日の傾向は最終レースより前のレース）。")

    def _write_csv(self, out_dir: Path, tables: list[Table]) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        frames = [pd.DataFrame(table.rows, columns=table.columns).assign(区分=table.title) for table in tables]
        pd.concat(frames).to_csv(out_dir / THEORY_CSV, index=False, encoding="utf-8-sig")
