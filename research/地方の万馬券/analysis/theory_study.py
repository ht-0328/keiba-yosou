"""理論の研究の流れ（段2）: 出走の表を長い期間で作り、理論ごとに同じ人気の馬全体と比べ、レースの条件ごとの荒れやすさも出す。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from .case_report import CaseReport
from .popularity_band import PopularityBand
from .race_condition_table import RaceConditionTable
from .race_theory_table import RaceTheoryTable
from .repository import TrifectaPayoutRepository
from .runner_enrichment import RunnerEnrichment
from .theory_catalog import FAVORITE_THEORIES, LONGSHOT_THEORIES
from .theory_check_table import TheoryCheckTable

#: 荒れやすさを見るレースの条件（``RaceConditionTable.race_table`` の列）。
RACE_CONDITIONS: tuple[str, ...] = ("頭数", "クラス", "競馬場", "距離", "馬場", "1番人気のオッズ", "1〜3番人気の支持率",
                                    "遠征馬の数", "転入初戦の数", "中央所属の数", "前走で前にいた馬の数", "連闘の数", "2歳戦")
#: 書く CSV。
THEORY_CSV = "理論の検証.csv"


@dataclass(frozen=True)
class TheoryStudySettings:
    date_from: date = date(2019, 1, 1)
    split: date = date(2024, 1, 1)
    min_heads: int = 11
    popularity: PopularityBand = PopularityBand()


@dataclass(frozen=True)
class TheoryStudy:
    con: duckdb.DuckDBPyConnection
    settings: TheoryStudySettings = TheoryStudySettings()

    def run(self, out_dir: Path) -> Path:
        s = self.settings
        runners = RunnerEnrichment(self.con, s.date_from, s.min_heads, s.popularity).load()
        checker = TheoryCheckTable(s.split)
        favorite_table = checker.build(runners, FAVORITE_THEORIES, title="1. 人気馬（1〜3番人気）の理論")
        longshot_table = checker.build(runners, LONGSHOT_THEORIES, title="2. 穴馬（中穴 4〜7番人気・大穴 8番人気以下）の理論")
        races = self._races(runners)
        race_table = RaceTheoryTable(s.split).build(races, RACE_CONDITIONS, title="3. 荒れやすいレースの条件")
        self._write_csv(out_dir, favorite_table, longshot_table)
        intro = (f"対象: {s.date_from} 以降の地方（ばんえいを除く）の {s.min_heads}頭以上の確定レースの出走 {len(runners):,} 頭。"
                 f"{s.split.year}年の前後の2つの期間で見る。人気の帯は {s.popularity.label}。")
        return CaseReport(out_dir).write("理論の検証", "地方の万馬券: 理論の検証", intro, [favorite_table, longshot_table, race_table])

    def _races(self, runners: pd.DataFrame) -> pd.DataFrame:
        conditions = RaceConditionTable().race_table(runners)
        first = runners.groupby("race_id")[["race_date"]].first()
        payouts = TrifectaPayoutRepository(self.con).load().set_index("race_id")
        return conditions.join(first).join(payouts, how="inner")

    def _write_csv(self, out_dir: Path, *tables) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        frames = [pd.DataFrame(table.rows, columns=table.columns) for table in tables]
        pd.concat(frames).to_csv(out_dir / THEORY_CSV, index=False, encoding="utf-8-sig")
