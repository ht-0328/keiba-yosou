"""過去の WIN5（2019年から）で、本線（今の買い目）と抑え（荒れる前提）の候補を精算し、探索期間で抑えを選び、確認期間で確かめる（段2 の 2.）。

元DB の読み方・確かめる日の作り方・配当の見積もり・組み方・精算は、道具「印の成績」の ``--win5`` と WIN5 の予想の部品をそのまま使う。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.repository import (
    Win5HistoryRepository,
    Win5LegRunnerHistoryRepository,
    Win5ScratchRepository,
)
from yosou.form_aptitude_win5_tickets.settlement import RACE_DATE, STRATEGY, Win5Outcomes

from 印の成績.win5_backtest_days import Win5BacktestDays
from 印の成績.win5_fold_estimators import Win5FoldEstimators
from 印の成績.win5_periods import CONFIRM, EXPLORE, Win5Periods
from 印の成績.win5_prediction_files import Win5PredictionFiles
from 印の成績.win5_strategy_summary import HIT_RATE, RECOVERY

from .hedge_adoption_judge import HedgeAdoptionJudge
from .hedge_candidate import CURRENT, NEW
from .hedge_candidates import CANDIDATES, NEW_HEDGE, RULE_HEDGE
from .hedge_day_bets import CANDIDATE, HEDGE_ONLY, KIND, MAIN_LABEL, WITH_HEDGE, HedgeDayBets
from .hedge_summary import BIG, HedgeSummary
from .hedge_table import HedgeTable
from .hedge_year_table import HedgeYearTable
from .upset_legs import UpsetLegs

_ALL_DAYS = date(9999, 12, 31)
PERIOD = "期間"


@dataclass(frozen=True)
class Win5HedgeResult:
    """表と、精算の行（CSV に書く）と、判定と、選んだ抑えと比べる決まりの抑えの候補の名前（``HedgeCandidate.label``）。"""

    tables: list[Table]
    settled: pd.DataFrame
    verdict: str
    chosen: str
    rule: str


@dataclass(frozen=True)
class Win5HedgeStudy:
    """``current`` は今のモデルの当日・前日の予測の pkl、``combined`` は人気薄を新しい確率に置き換えた当日・前日の pkl。
    ``handicap`` はハンデ戦のレースID。"""

    current: tuple[Path, Path]
    combined: tuple[Path, Path]
    handicap: frozenset[str]

    def run(self, con: duckdb.DuckDBPyConnection) -> Win5HedgeResult:
        history = Win5HistoryRepository(con).read(_ALL_DAYS)
        scratches = Win5ScratchRepository(con).read(_ALL_DAYS)
        runners = Win5LegRunnerHistoryRepository(con).read(_ALL_DAYS)
        outcomes = Win5Outcomes().of(history, scratches)
        current = Win5PredictionFiles(*self.current).load()
        days_current, _ = Win5BacktestDays().of(history, runners, current)
        days_new = {day.race_date: day for day in Win5BacktestDays().of(history, runners, Win5PredictionFiles(*self.combined).load())[0]}
        estimators = Win5FoldEstimators().of(history, current.folds)
        bets = HedgeDayBets(history, UpsetLegs(self.handicap))
        rows = []
        for count, day in enumerate(days_current, start=1):
            if day.race_date in days_new:
                rows.extend(bets.settle({CURRENT: day, NEW: days_new[day.race_date]}, CANDIDATES, estimators[day.fold], outcomes[day.race_date]))
            if count % 50 == 0:
                print(f"WIN5 の {count}/{len(days_current)} 日を精算しました", file=sys.stderr, flush=True)
        settled = pd.DataFrame(rows)
        settled[PERIOD] = settled[RACE_DATE].map(Win5Periods().label_of)
        return self._result(settled)

    def _result(self, settled: pd.DataFrame) -> Win5HedgeResult:
        summaries = {period: HedgeSummary().of(settled.loc[settled[PERIOD] == period]) for period in (EXPLORE, CONFIRM)}
        candidates = settled.drop_duplicates(STRATEGY).set_index(STRATEGY)[[KIND, CANDIDATE]]
        chosen = self._best(summaries[EXPLORE], candidates, NEW_HEDGE)
        rule = self._best(summaries[EXPLORE], candidates, RULE_HEDGE)
        compared = [MAIN_LABEL, f"{WITH_HEDGE}: {chosen}", f"{HEDGE_ONLY}: {chosen}", f"{WITH_HEDGE}: {rule}", f"{HEDGE_ONLY}: {rule}"]
        verdict, reasons = HedgeAdoptionJudge().judge(self._by_period(summaries, compared[1]), self._by_period(summaries, MAIN_LABEL))
        table = HedgeTable()
        explore_rows = [MAIN_LABEL, *[name for name in summaries[EXPLORE][STRATEGY] if name.startswith(WITH_HEDGE)]]
        tables = [
            Table(["項目", "内容"], [["本線", MAIN_LABEL], ["選んだ抑え（探索期間で、本線＋抑えの回収率がいちばん高いもの）", chosen],
                                    ["比べる決まりの抑え（同じ選び方）", rule], ["判定", verdict], *[["理由", text] for text in reasons]],
                  title="WIN5 の本線と抑えの確かめの判定",
                  note="2025年〜は WIN5 の買い方の確かめで使うのが3回目。採用の決め手は、2026年11月以降の毎週の答え合わせに置く。"),
            table.build(summaries[EXPLORE], f"{EXPLORE}: 本線だけと、本線＋抑えの全部の候補", order=explore_rows),
            table.build(summaries[EXPLORE], f"{EXPLORE}: 選んだ抑えと比べる相手", order=compared),
            table.build(summaries[CONFIRM], f"{CONFIRM}: 選んだ抑えと比べる相手", order=compared),
            HedgeYearTable().build(settled, compared, "年ごとの成績"),
        ]
        return Win5HedgeResult(tables, settled, verdict, chosen, rule)

    @staticmethod
    def _best(summary: pd.DataFrame, candidates: pd.DataFrame, group: str) -> str:
        """その組の抑えのうち、本線＋抑えの回収率がいちばん高いもの（同じなら 100万円以上の的中が多く、的中率が高いもの）の候補の名前。"""
        names = candidates.index[(candidates[KIND] == WITH_HEDGE) & candidates[CANDIDATE].str.startswith(group)]
        ranked = summary.loc[summary[STRATEGY].isin(names)].sort_values([RECOVERY, BIG, HIT_RATE], ascending=False, kind="stable")
        return str(candidates.loc[ranked[STRATEGY].iloc[0], CANDIDATE])

    @staticmethod
    def _by_period(summaries: dict[str, pd.DataFrame], name: str) -> dict[str, pd.Series]:
        """期間の名前 → その買い方の成績の1行（その期間に1日も買わなければ、数の列が全部 0 の行）。"""
        return {period: summary.set_index(STRATEGY).reindex([name]).iloc[0].fillna(0) for period, summary in summaries.items()}
