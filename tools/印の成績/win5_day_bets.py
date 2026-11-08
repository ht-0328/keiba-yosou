"""過去の WIN5 の1日について、40 通りの買い方と比べる相手の買い目を組み、精算する。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd

from yosou.form_aptitude_win5_tickets.formation import (
    BUDGETS,
    MIN_VALUES,
    ORDERINGS,
    Formation,
    FormationSearch,
    FormationValue,
)
from yosou.form_aptitude_win5_tickets.payout import PayoutEstimator, PayoutPool, PoolSizeEstimate
from yosou.form_aptitude_win5_tickets.repository.win5_columns import HORSE_NO, WIN_ODDS
from yosou.form_aptitude_win5_tickets.settlement import (
    HIT,
    PAYOUT,
    RACE_DATE,
    STAKE,
    STRATEGY,
    PopularityFormation,
    RuleFormations,
    Win5Outcome,
    Win5Settlement,
)

from 印の成績.win5_backtest_day import Win5BacktestDay
from 印の成績.win5_strategy import Win5Strategy

#: 精算の結果の行に足す列: 買い方の種類（この予想・比べる相手）・予算・日の期待値（この予想だけ）・キャリーオーバーの日か。
KIND = "種類"
BUDGET = "予算"
EXPECTED_VALUE = "日の期待値"
CARRY_DAY = "キャリーオーバーの日"
#: 買い方の種類。
OURS = "この予想"
BASELINE = "比べる相手"
#: 比べる相手の名前。
RULE = "ルール集のWIN5のルール（240点）"
RULE_CARRY = "ルール集のWIN5のルール（240点・キャリーオーバーの日だけ）"
_POPULARITY = "人気だけ（{budget}点）"
#: 40 通りの買い方（並べ方 × 予算 × 線）。
STRATEGIES: tuple[Win5Strategy, ...] = tuple(
    Win5Strategy(ordering, budget, line) for ordering in ORDERINGS for budget in BUDGETS for line in MIN_VALUES
)


def popularity_label(budget: int) -> str:
    """比べる相手 (2)（人気だけ）の、予算ごとの名前。"""
    return _POPULARITY.format(budget=budget)


class Win5DayBets:
    """1日について、この予想の 40 通り（並べ方ごとに ``FormationSearch.best_by_budget`` で予算ごとの買い目を組み、日の期待値が線以上なら買う）と、
    比べる相手（ルール集の 240点・その「キャリーオーバーの日だけ」・人気だけの予算ごと）の買い目を組み、``Win5Settlement`` で精算する
    （設計書「近走と適性からWIN5の買い目を決める」16 の 4.・5.）。

    返すのは買った買い方の行だけ（見送りの日は入れない）。払戻に回るお金の見込みは、その日より前の WIN5 から見積もった発売票数と、
    その日のキャリーオーバー金額初期（``PoolSizeEstimate``・``PayoutPool``）。
    """

    def __init__(self, history: pd.DataFrame) -> None:
        self._history = history
        self._pool_size = PoolSizeEstimate()
        self._settlement = Win5Settlement()

    def settle(self, day: Win5BacktestDay, estimator: PayoutEstimator, outcome: Win5Outcome) -> list[dict[str, object]]:
        pool = PayoutPool(self._pool_size.of(self._history, date.fromisoformat(day.race_date), day.saturday), day.carry)
        rows = self._ours(day, estimator, pool, outcome)
        popularity = [self._popularity(leg) for leg in day.legs]
        rule = RuleFormations().of(popularity)
        rows.append(self._row(day, RULE, BASELINE, 240, rule, outcome))
        if day.carry > 0:
            rows.append(self._row(day, RULE_CARRY, BASELINE, 240, rule, outcome))
        for budget in BUDGETS:
            formation = PopularityFormation().of(popularity, budget)
            rows.append(self._row(day, popularity_label(budget), BASELINE, budget, (formation,), outcome))
        return rows

    def _ours(self, day: Win5BacktestDay, estimator: PayoutEstimator, pool: PayoutPool,
              outcome: Win5Outcome) -> list[dict[str, object]]:
        """40 通りのうち、日の期待値が線以上で買った買い方の行。"""
        rows = []
        value = FormationValue(estimator)
        for ordering in ORDERINGS:
            choices = FormationSearch(ordering, value).best_by_budget(list(day.legs), BUDGETS, pool)
            for strategy in STRATEGIES:
                choice = choices[strategy.budget]
                if strategy.ordering is ordering and choice.expected_value >= strategy.line:
                    row = self._row(day, strategy.label, OURS, strategy.budget, (choice.formation,), outcome)
                    rows.append({**row, EXPECTED_VALUE: choice.expected_value})
        return rows

    def _row(self, day: Win5BacktestDay, label: str, kind: str, budget: int, formations: Sequence[Formation],
             outcome: Win5Outcome) -> dict[str, object]:
        settled = [self._settlement.settle(formation, outcome) for formation in formations]
        return {
            STRATEGY: label, KIND: kind, BUDGET: budget, RACE_DATE: day.race_date, STAKE: sum(each.stake for each in settled),
            PAYOUT: sum(each.payout for each in settled), HIT: any(each.hit for each in settled), CARRY_DAY: day.carry > 0,
            EXPECTED_VALUE: float("nan"),
        }

    def _popularity(self, leg: pd.DataFrame) -> list[int]:
        """人気の順（確定の単勝オッズの小さい順。同じなら馬番の小さい順）の馬番。"""
        ordered = leg.sort_values([WIN_ODDS, HORSE_NO], kind="stable")
        return [int(number) for number in ordered[HORSE_NO]]
