"""事例の研究の流れ: 元DB を読み、馬に帯と事情を付け、10万馬券のレースを集めて、表を書く。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table

from .case_list_table import CaseListTable
from .case_report import CaseReport
from .circumstance_share_table import CircumstanceShareTable
from .outcome_pattern_table import PATTERN_COUNTS, PATTERN_ORDERED, OutcomePatternTable
from .payout_band import BIG, HUGE, PAYOUT_BANDS, PayoutBand
from .popularity_band import FAVORITE, LONGSHOT, MIDDLE, PopularityBand
from .race_condition_table import RaceConditionTable
from .repository import TrifectaPayoutRepository
from .runner_circumstances import CIRCUMSTANCES
from .runner_enrichment import RunnerEnrichment

_LOST_FINISH = 4
#: 書く CSV の名前。
RUNNERS_CSV = "事例の馬.csv"
RACES_CSV = "事例のレース.csv"


@dataclass(frozen=True)
class CaseStudySettings:
    """事例の集め方。"""

    date_from: date = date(2024, 1, 1)
    min_heads: int = 11
    popularity: PopularityBand = PopularityBand()
    payout: PayoutBand = PayoutBand()
    list_limit: int = 40


@dataclass(frozen=True)
class CaseStudy:
    """元DB（地方）から事例の表を作る。``run`` が表を書き、書いた場所を返す。"""

    con: duckdb.DuckDBPyConnection
    settings: CaseStudySettings = CaseStudySettings()

    def run(self, out_dir: Path) -> Path:
        runners = self._runners()
        races = self._races(runners)
        event_ids = races.index[races["payout_band"].isin((BIG, HUGE))]
        tables = [
            self._band_summary(races),
            *self._pattern_tables(races),
            *self._share_tables(runners, races, event_ids),
            RaceConditionTable().build(RaceConditionTable().race_table(runners), event_ids,
                                       title="6. レースの条件（10万馬券以上のレース と 全レース）"),
            CaseListTable(self.settings.list_limit).build(runners, races, title="7. 事例の一覧（配当の高い順）"),
        ]
        self._write_csv(out_dir, runners, races, event_ids)
        return CaseReport(out_dir).write("事例", "地方の万馬券: 事例", self._intro(races), tables)

    # --- 読む・付ける -------------------------------------------------------------------------------------------

    def _runners(self) -> pd.DataFrame:
        s = self.settings
        return RunnerEnrichment(self.con, s.date_from, s.min_heads, s.popularity).load()

    def _races(self, runners: pd.DataFrame) -> pd.DataFrame:
        first = runners.groupby("race_id")[["race_date", "venue", "race_no", "class_name", "field_size"]].first()
        payouts = TrifectaPayoutRepository(self.con).load().set_index("race_id")
        races = first.join(payouts, how="inner")
        races["payout_band"] = self.settings.payout.band_of(races["trifecta_payout"])
        placed = runners[runners["finish"] <= 3]
        patterns = OutcomePatternTable().patterns(placed).set_index("race_id")
        return races.join(patterns, how="inner")

    # --- 表 ---------------------------------------------------------------------------------------------------

    def _band_summary(self, races: pd.DataFrame) -> Table:
        total = len(races)
        rows = [{"配当の帯": band, "レース数": int((races["payout_band"] == band).sum()),
                 "割合": f"{(races['payout_band'] == band).mean():.1%}",
                 "配当の中央値": int(races.loc[races["payout_band"] == band, "trifecta_payout"].median()) if (races["payout_band"] == band).any() else 0}
                for band in PAYOUT_BANDS]
        rows.append({"配当の帯": "全部", "レース数": total, "割合": "100%", "配当の中央値": int(races["trifecta_payout"].median())})
        return Table.from_records(rows, ("配当の帯", "レース数", "割合", "配当の中央値"), title="1. 3連単の配当の帯ごとのレース数",
                                  note=self.settings.payout.label)

    def _pattern_tables(self, races: pd.DataFrame) -> list[Table]:
        maker = OutcomePatternTable()
        return [
            maker.build(races, PATTERN_COUNTS, title="2. 配当の帯 × 決着の型（順不同。人気馬・中穴・大穴から何頭ずつ来たか）"),
            maker.build(races, PATTERN_ORDERED, title="3. 配当の帯 × 決着の型（1着→2着→3着の順）"),
        ]

    def _share_tables(self, runners: pd.DataFrame, races: pd.DataFrame, event_ids: pd.Index) -> list[Table]:
        in_event = runners["race_id"].isin(event_ids)
        lost = (runners["finish"] >= _LOST_FINISH) | runners["finish"].isna()
        placed = runners["finish"] <= 3
        favorite, middle, longshot = (runners["band"] == band for band in (FAVORITE, MIDDLE, LONGSHOT))
        maker = CircumstanceShareTable()
        return [
            maker.build(runners[favorite & in_event & lost], runners[favorite], title="4-1. 崩れた人気馬（10万馬券以上のレースで4着以下の 1〜3番人気） と 1〜3番人気全体",
                        note="倍率が大きい事情ほど、人気馬が崩れたレースに多い。"),
            maker.build(runners[favorite & lost], runners[favorite], title="4-2. 崩れた人気馬（全レースで4着以下の 1〜3番人気） と 1〜3番人気全体",
                        note="配当にかかわらず、人気馬が4着以下になった出走全体で見たもの。"),
            maker.build(runners[middle & in_event & placed], runners[middle], title="5-1. 来た中穴（10万馬券以上のレースで3着以内の 4〜7番人気） と 4〜7番人気全体"),
            maker.build(runners[longshot & in_event & placed], runners[longshot], title="5-2. 来た大穴（10万馬券以上のレースで3着以内の 8番人気以下） と 8番人気以下全体"),
            maker.build(runners[middle & placed], runners[middle], title="5-3. 来た中穴（全レースで3着以内） と 4〜7番人気全体"),
            maker.build(runners[longshot & placed], runners[longshot], title="5-4. 来た大穴（全レースで3着以内） と 8番人気以下全体"),
        ]

    def _intro(self, races: pd.DataFrame) -> str:
        s = self.settings
        return (f"対象: {s.date_from} 以降の地方（ばんえいを除く）の確定レースのうち、{s.min_heads}頭以上で 3連単の払戻があるもの {len(races):,} レース。"
                f"人気の帯は {s.popularity.label}。配当の帯は {s.payout.label}。\n\n"
                "事情（4・5・7 の表）はレースの前に分かる情報だけから機械的に付けた（意味は 4-1 の表の右の列）。"
                "表の数字は地方競馬DATA の集計で、馬名・騎手名は載せていない。")

    def _write_csv(self, out_dir: Path, runners: pd.DataFrame, races: pd.DataFrame, event_ids: pd.Index) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        columns = ["race_id", "race_date", "venue", "race_no", "class_name", "field_size", "horse_no", "popularity", "win_odds",
                   "finish", "band", *CIRCUMSTANCES]
        runners[runners["race_id"].isin(event_ids)][columns].to_csv(out_dir / RUNNERS_CSV, index=False, encoding="utf-8-sig")
        races.to_csv(out_dir / RACES_CSV, encoding="utf-8-sig")
