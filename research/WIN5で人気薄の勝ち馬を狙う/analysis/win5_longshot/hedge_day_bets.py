"""WIN5 の1日について、本線（今の買い目）を組み、本線を買う日に抑えの候補ごとの買い目を組んで、「本線だけ」「本線＋抑え」「抑えだけ」を精算する。

組み方・見積もり・精算は WIN5 の予想の部品（``FormationSearch``・``FormationValue``・``Win5Settlement``）。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd

from yosou.form_aptitude_win5_tickets.formation import Formation, FormationChoice, FormationSearch, FormationValue, LegOrdering
from yosou.form_aptitude_win5_tickets.payout import PayoutEstimator, PayoutPool, PoolSizeEstimate
from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY, Win5Outcome, Win5Settlement

from 印の成績.win5_backtest_day import Win5BacktestDay

from .hedge_candidate import CURRENT, HedgeCandidate
from .hedge_candidates import MAIN_BUDGET, MAIN_LINE
from .hedge_formation import HedgeFormation
from .longshot_coverage import LongshotCoverage
from .upset_legs import UpsetLegs

#: 結果の行に足す列。
KIND, CANDIDATE = "種類", "抑えの候補"
WIN_PAYOUT = "当たった組の100円あたりの払戻"
LONGSHOT_LEGS, COVERED = "人気薄が勝ったレース", "そのうち買い目に入っていた"
MAIN_SIZES, HEDGE_SIZES = "本線の頭数", "抑えの頭数"
MAIN_PICKS, HEDGE_PICKS = "本線の買い目", "抑えの買い目"
#: 種類と、本線だけの名前。
MAIN_ONLY, WITH_HEDGE, HEDGE_ONLY = "本線だけ", "本線＋抑え", "抑えだけ"
MAIN_LABEL = f"本線だけ（今の買い目: 1着の確率の順・{MAIN_BUDGET}点・線 {MAIN_LINE:.2f}）"


class HedgeDayBets:
    """``days`` は 確率の元 → その日の確かめる日（今のモデル・新しい確率）。本線は今のモデルの確率で組む。"""

    def __init__(self, history: pd.DataFrame, upset: UpsetLegs) -> None:
        self._history = history
        self._upset = upset
        self._pool_size = PoolSizeEstimate()
        self._settlement = Win5Settlement()
        self._coverage = LongshotCoverage()

    def settle(self, days: dict[str, Win5BacktestDay], candidates: Sequence[HedgeCandidate], estimator: PayoutEstimator,
               outcome: Win5Outcome) -> list[dict[str, object]]:
        current = days[CURRENT]
        pool = PayoutPool(self._pool_size.of(self._history, date.fromisoformat(current.race_date), current.saturday), current.carry)
        value = FormationValue(estimator)
        main = FormationSearch(LegOrdering.BY_PROBABILITY, value).best(list(current.legs), MAIN_BUDGET, pool)
        if main.expected_value < MAIN_LINE:
            return []
        rows = [self._row(MAIN_LABEL, MAIN_ONLY, "", current, [main.formation], outcome, main.formation, None)]
        cache: dict[tuple, FormationChoice | None] = {}
        for candidate in candidates:
            rows.extend(self._hedge_rows(days[candidate.source], current, candidate, main.formation, value, pool, outcome, cache))
        return rows

    def _hedge_rows(self, day: Win5BacktestDay, current: Win5BacktestDay, candidate: HedgeCandidate, main: Formation,
                    value: FormationValue, pool: PayoutPool, outcome: Win5Outcome,
                    cache: dict[tuple, FormationChoice | None]) -> list[dict[str, object]]:
        key = (candidate.source, candidate.longshot_order, candidate.upset_count, candidate.longshots, candidate.budget)
        if key not in cache:
            upset = self._upset.of(day.legs)[:candidate.upset_count]
            cache[key] = HedgeFormation(value).best(day.legs, main, upset, candidate, pool) if upset else None
        hedge = cache[key]
        if hedge is not None and candidate.line is not None and hedge.expected_value < candidate.line:
            hedge = None
        hedges = [hedge.formation] if hedge is not None else []
        rows = [self._row(f"{WITH_HEDGE}: {candidate.label}", WITH_HEDGE, candidate.label, current, [main, *hedges], outcome, main,
                          hedge.formation if hedge is not None else None)]
        if hedge is not None:
            rows.append(self._row(f"{HEDGE_ONLY}: {candidate.label}", HEDGE_ONLY, candidate.label, current, hedges, outcome, None,
                                  hedge.formation))
        return rows

    def _row(self, label: str, kind: str, candidate: str, day: Win5BacktestDay, formations: list[Formation], outcome: Win5Outcome,
             main: Formation | None, hedge: Formation | None) -> dict[str, object]:
        settled = [self._settlement.settle(formation, outcome) for formation in formations]
        hit = any(each.hit for each in settled)
        legs, covered = self._coverage.of(formations, day.legs, outcome)
        return {
            STRATEGY: label, KIND: kind, CANDIDATE: candidate, RACE_DATE: day.race_date, STAKE: sum(each.stake for each in settled),
            PAYOUT: sum(each.payout for each in settled), HIT: hit, WIN_PAYOUT: self._win_payout(outcome) if hit else 0,
            LONGSHOT_LEGS: legs, COVERED: covered, MAIN_SIZES: main.sizes_text() if main is not None else "",
            HEDGE_SIZES: hedge.sizes_text() if hedge is not None else "",
            MAIN_PICKS: self._picks(main), HEDGE_PICKS: self._picks(hedge),
        }

    @staticmethod
    def _picks(formation: Formation | None) -> str:
        """買い目の馬番（レースは「/」、馬は「,」で区切る）。"""
        if formation is None:
            return ""
        return "/".join(",".join(str(number) for number in picks) for picks in formation.legs)

    @staticmethod
    def _win_payout(outcome: Win5Outcome) -> int:
        return max((payout for _, payout in outcome.winners), default=0)
