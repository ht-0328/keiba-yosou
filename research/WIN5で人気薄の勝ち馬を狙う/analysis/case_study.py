"""事例の研究の流れ（段1）: 元DB を読み、出走の表に列と型を足し、人気薄が勝ったレースの表を作って reports/ に書く。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table

from .case_report import CaseReport
from .enrichment.fold_win_predictions import DEFAULT_PREDICTIONS, FoldWinPredictions
from .enrichment.race_market_shape import LONGSHOT_POPULARITY
from .enrichment.runner_enrichment import RunnerEnrichment
from .enrichment.win5_record_probabilities import DEFAULT_RECORDS, Win5RecordProbabilities
from .repository import RunnerFactsRepository, Win5LegRepository
from .tables.case_count_table import CaseCountTable
from .tables.case_list import CaseList
from .tables.flag_share_table import FlagShareTable
from .tables.focus_case_table import FocusCaseTable
from .tables.longshot_distribution_table import LongshotDistributionTable
from .tables.longshot_rank_table import LongshotRankTable
from .tables.model_uplift_table import ModelUpliftTable
from .tables.outcome_side_table import OutcomeSideTable
from .tables.period_split_table import PeriodSplitTable
from .tables.race_type_table import RaceTypeTable
from .tables.winner_popularity_table import WinnerPopularityTable
from .theory.clue_catalog import CLUES
from .theory.race_table import RaceTable
from .theory.runner_type_catalog import NO_TYPE, RUNNER_TYPES
from .theory.runner_type_flags import RunnerTypeFlags

#: 書くファイルの名前。
REPORT_NAME = "事例"
WIN5_CSV = "WIN5の事例.csv"
FLAT_CSV = "平地の事例.csv"
#: 平地の全体で見る切り口と、WIN5 の対象レースで見る切り口。
FLAT_CUTS: tuple[str, ...] = ("年", "競馬場", "芝ダ", "距離", "頭数", "クラス", "重量種別", "馬場状態", "1番人気の単勝オッズ",
                              "10番人気以下のオッズから見た勝率の合計")
WIN5_CUTS: tuple[str, ...] = ("年", "競馬場", "芝ダ", "頭数", "クラス", "重量種別", "1番人気の単勝オッズ", "10番人気以下のオッズから見た勝率の合計")
#: 平地の代表的な事例として、型ごとに出す新しい順の頭数。
EXAMPLES_PER_TYPE = 3


@dataclass(frozen=True)
class CaseStudySettings:
    """事例の集め方。``history_from`` は過去走・人と血統の前の年までの成績をたどるために読み始める日。
    ``predictions`` は今のモデルの区切りごとの当日の1着の予測、``records`` は WIN5 の予想の記録の置き場所。"""

    date_from: date = date(2019, 1, 1)
    history_from: date = date(2012, 1, 1)
    focus_date: str = "2026-11-08"
    predictions: Path = DEFAULT_PREDICTIONS
    records: Path = DEFAULT_RECORDS


@dataclass(frozen=True)
class CaseStudy:
    """元DB（中央）から事例の表を作る。``run`` が表と CSV を書き、Markdown の場所を返す。"""

    con: duckdb.DuckDBPyConnection
    settings: CaseStudySettings = CaseStudySettings()

    def run(self, out_dir: Path) -> Path:
        history = RunnerFactsRepository(self.con).load(self.settings.history_from)
        legs = Win5LegRepository(self.con).load(self.settings.date_from)
        predictions = (FoldWinPredictions(self.settings.predictions).load(), Win5RecordProbabilities(self.settings.records).load())
        runners = RunnerTypeFlags().add(RunnerEnrichment(predictions, self.settings.date_from).build(history, legs))
        sections = self.sections(runners, history)
        self._write_csv(runners, out_dir)
        return CaseReport(out_dir).write(REPORT_NAME, "WIN5で人気薄の勝ち馬を狙う: 事例", self._intro(), sections)

    def sections(self, runners: pd.DataFrame, history: pd.DataFrame) -> list[tuple[str, list[Table]]]:
        """報告の節と表（元DB を読んだあとの部分。テストから呼べるよう分けてある）。"""
        races = RaceTable(LONGSHOT_POPULARITY).build(runners)
        win5_races = races.loc[races["win5_leg"].notna()]
        longshots = runners.loc[runners["popularity"] >= LONGSHOT_POPULARITY]
        win5_longshots = longshots.loc[longshots["win5_leg"].notna()]
        distribution = LongshotDistributionTable()
        return [
            ("事例の数", [*CaseCountTable(LONGSHOT_POPULARITY).build(races), WinnerPopularityTable().build(races)]),
            ("平地の全レースの分布",
             [distribution.build(races, cut, f"平地: {cut}ごと") for cut in FLAT_CUTS]
             + [distribution.build(races, "コースの単位（競馬場・芝ダ・距離・馬場状態）", "平地: コースの単位ごと（人気薄が勝った数の多い順）", by_count=True)]),
            ("WIN5 の対象レースの分布", [distribution.build(win5_races, cut, f"WIN5: {cut}ごと") for cut in WIN5_CUTS]),
            ("レースの側の型", [RaceTypeTable().build(races, "レースの側の型（平地の全レース）"),
                           RaceTypeTable().build(win5_races, "レースの側の型（WIN5 の対象レース）")]),
            ("馬の側の手がかり", [FlagShareTable().build(longshots, CLUES, "手がかりごとの人気薄の勝ち（平地の全レース）"),
                            FlagShareTable().build(win5_longshots, CLUES, "手がかりごとの人気薄の勝ち（WIN5 の対象レース）")]),
            ("馬の側の型", [FlagShareTable().build(longshots, RUNNER_TYPES, "馬の側の型（平地の全レース）", extra=(NO_TYPE,)),
                         FlagShareTable().build(win5_longshots, RUNNER_TYPES, "馬の側の型（WIN5 の対象レース）", extra=(NO_TYPE,)),
                         PeriodSplitTable().build(longshots, RUNNER_TYPES, "馬の側の型を前半と後半の年に分けたとき（平地の全レース）")]),
            ("人気薄の中の並べ方", [LongshotRankTable().build(longshots, "人気薄の中で勝ち馬を上位に置けたか（平地の全レース）"),
                             LongshotRankTable().build(win5_longshots, "人気薄の中で勝ち馬を上位に置けたか（WIN5 の対象レース）")]),
            ("今のモデルの見方", [*ModelUpliftTable().build(longshots, "平地の全レース"), *ModelUpliftTable().build(win5_longshots, "WIN5 の対象レース")]),
            ("結果側の様子", [OutcomeSideTable(LONGSHOT_POPULARITY).build(runners.loc[runners["finish"] == 1])]),
            ("詳しく見る日", FocusCaseTable().build(runners, history, self.settings.focus_date, LONGSHOT_POPULARITY)),
            ("事例の一覧", [CaseList().table(win5_longshots.loc[win5_longshots["finish"] == 1], "WIN5 の対象レースで人気薄が勝った全部の事例"),
                         CaseList().table(self._examples(longshots), "平地の代表的な事例（馬の側の型ごとに新しい順に3つ）",
                                          note=f"全部は {FLAT_CSV}")]),
        ]

    @staticmethod
    def _examples(longshots: pd.DataFrame) -> pd.DataFrame:
        winners = longshots.loc[longshots["finish"] == 1].sort_values("race_date", ascending=False)
        names = [rule.name for rule in RUNNER_TYPES] + [NO_TYPE]
        picked = [winners.loc[winners[name]].head(EXAMPLES_PER_TYPE) for name in names]
        return pd.concat(picked).drop_duplicates(["race_id", "horse_no"])

    @staticmethod
    def _write_csv(runners: pd.DataFrame, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        winners = runners.loc[(runners["popularity"] >= LONGSHOT_POPULARITY) & (runners["finish"] == 1)]
        listing = CaseList()
        listing.frame(winners.loc[winners["win5_leg"].notna()]).to_csv(out_dir / WIN5_CSV, index=False, encoding="utf-8-sig")
        listing.frame(winners).to_csv(out_dir / FLAT_CSV, index=False, encoding="utf-8-sig")

    def _intro(self) -> str:
        s = self.settings
        return (f"{s.date_from.isoformat()} 以降の中央の平地のレースで、{LONGSHOT_POPULARITY}番人気以下（確定の単勝人気）が勝った事例。"
                "人気・オッズは確定オッズ（締め切り前とほぼ同じとみなす）。今のモデルの1着の確率は、区切りごとの予測（その半年より前だけで学び直したもの）、"
                "区切りの無い最近の WIN5 の日は WIN5 の予想の記録の値。結果側の列（ペース・4角・上がり・着差）は理解のためだけに使う。"
                f"一覧の全部は {WIN5_CSV} と {FLAT_CSV}。研究の文書は research/WIN5で人気薄の勝ち馬を狙う/docs/。")
