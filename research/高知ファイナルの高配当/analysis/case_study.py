"""事例の研究の流れ（段1）: ファイナルレースを集め、配当の帯と決着の型を数え、荒れたレースを1レースずつ並べて書く。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 地方の万馬券.analysis.case_report import CaseReport
from 地方の万馬券.analysis.outcome_pattern_table import PATTERN_COUNTS, PATTERN_ORDERED, OutcomePatternTable
from 地方の万馬券.analysis.payout_band import PayoutBand

from .case_list_table import CaseListTable
from .payout_band_table import PayoutBandTable
from .popularity_band import PopularityBand
from .repository import TrifectaPayoutRepository
from .runner_tables import RunnerTables

REPORT_NAME = "事例"
_RACE_COLUMNS = ["race_date", "race_no", "class_name", "distance_m", "condition", "field_size"]
_PLACED_FINISH = 3


@dataclass(frozen=True)
class CaseStudySettings:
    """事例の集め方。``list_from`` は1レースずつ並べる事例の最初の開催日（数える表は全期間）。"""

    min_heads: int = 9
    popularity: PopularityBand = PopularityBand()
    payout: PayoutBand = PayoutBand()
    list_from: date = date(2024, 1, 1)
    list_limit: int = 20


@dataclass(frozen=True)
class CaseStudy:
    """元DB（地方）から事例の表を作る。``run`` が表を書き、書いた場所を返す。"""

    con: duckdb.DuckDBPyConnection
    settings: CaseStudySettings = CaseStudySettings()

    def run(self, out_dir: Path) -> Path:
        s = self.settings
        runs, runners = RunnerTables(self.con, s.min_heads, s.popularity).load()
        races = self._races(runners)
        patterns = OutcomePatternTable()
        recent_races = races[races["race_date"] >= pd.Timestamp(s.list_from)]
        tables = [
            PayoutBandTable(s.payout).build(races, title="1. 3連単の配当の帯ごとのレース数"),
            patterns.build(races, PATTERN_COUNTS, title="2. 配当の帯 × 決着の型（順不同。人気馬・中穴・大穴から何頭ずつ来たか）"),
            patterns.build(races, PATTERN_ORDERED, title="3. 配当の帯 × 決着の型（1着→2着→3着の順）"),
            *CaseListTable(s.list_limit).build(runs, runners, recent_races),
        ]
        return CaseReport(out_dir).write(REPORT_NAME, "高知ファイナルの高配当: 事例", self._intro(races), tables)

    def _races(self, runners: pd.DataFrame) -> pd.DataFrame:
        """レースごとの表（``race_id`` が index）: 条件・3連単の払戻・配当の帯・決着の型。払戻か1〜3着がそろわないレースは出さない。"""
        first = runners.groupby("race_id")[_RACE_COLUMNS].first()
        payouts = TrifectaPayoutRepository(self.con).load().set_index("race_id")
        races = first.join(payouts, how="inner")
        races["payout_band"] = self.settings.payout.band_of(races["trifecta_payout"])
        placed = runners[runners["finish"] <= _PLACED_FINISH]
        return races.join(OutcomePatternTable().patterns(placed).set_index("race_id"), how="inner")

    def _intro(self, races: pd.DataFrame) -> str:
        s = self.settings
        return (f"対象: 高知のファイナルレース（その日の最終レース）のうち、{s.min_heads}頭以上で 3連単の払戻がある {len(races):,} レース"
                f"（{races['race_date'].min():%Y-%m-%d} 〜 {races['race_date'].max():%Y-%m-%d}）。"
                f"人気の帯は {s.popularity.label}。配当の帯は {s.payout.label}。\n\n"
                f"表 1〜3 のあとは、{s.list_from} 以降のレースを 3連単の配当の高い順に {s.list_limit} レース、出走馬ごとに並べた事例。"
                "近走は高知の出走だけを古い順に「クラス 距離: 人気・着順（着差・4コーナーの順位）」で書き、ファイナルレースだった走は頭に F を付けた。"
                "ファイナルの出走/3着以内 は、そのレースより前のファイナルレースの出走数と3着以内の数。馬名・騎手名は載せていない。")
