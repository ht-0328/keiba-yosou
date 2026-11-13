"""過去の WIN5 の1日について、段階の予算の候補ごとに買う予算を決め、その買い目を精算する。"""

from __future__ import annotations

from collections.abc import Sequence

from yosou.form_aptitude_win5_tickets.formation import FormationChoice
from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY, Win5Outcome, Win5Settlement

from 印の成績.win5_backtest_day import Win5BacktestDay
from 印の成績.win5_bet_columns import BUDGET, CARRY_DAY, EXPECTED_VALUE, FAVORITE_PRODUCT, KIND, LARGE_DAY, TIERED
from 印の成績.win5_tier_strategy import TIER_CANDIDATES, TIER_JUDGE, Win5TierStrategy


class Win5TierBets:
    """設計書「近走と適性からWIN5の買い目を決める」16 の「段階の予算の確かめ」。判断用の買い目（``TIER_JUDGE``。1着の確率の順・50点）の
    日の期待値が線以上の日だけ、候補ごとに多く買う日かを決めて（``Win5TierStrategy.is_large``）、その予算の買い目を ``Win5Settlement`` で精算する。
    買い目は ``Win5DayBets`` が ``FormationSearch.best_by_budget`` で予算ごとに組んだもの（``choices``）を使い、ここでは組み直さない。"""

    def __init__(self, strategies: Sequence[Win5TierStrategy] = TIER_CANDIDATES) -> None:
        self._strategies = tuple(strategies)
        self._settlement = Win5Settlement()

    def rows(self, day: Win5BacktestDay, choices: dict[int, FormationChoice], favorite_product: float,
             outcome: Win5Outcome) -> list[dict[str, object]]:
        """``choices`` は判断用の並べ方（1着の確率の順）で組んだ、予算 → いちばん良い買い目。見送りの日は空。"""
        judge = choices[TIER_JUDGE.budget]
        if judge.expected_value < TIER_JUDGE.line:
            return []
        return [self._row(day, strategy, judge, choices, favorite_product, outcome) for strategy in self._strategies]

    def _row(self, day: Win5BacktestDay, strategy: Win5TierStrategy, judge: FormationChoice, choices: dict[int, FormationChoice],
             favorite_product: float, outcome: Win5Outcome) -> dict[str, object]:
        large_day = strategy.is_large(judge, choices[strategy.small], choices[strategy.large], favorite_product)
        budget = strategy.budget_for(large_day)
        settled = self._settlement.settle(choices[budget].formation, outcome)
        return {
            STRATEGY: strategy.label, KIND: TIERED, BUDGET: budget, RACE_DATE: day.race_date, STAKE: settled.stake, PAYOUT: settled.payout,
            HIT: settled.hit, CARRY_DAY: day.carry > 0, EXPECTED_VALUE: judge.expected_value, LARGE_DAY: large_day,
            FAVORITE_PRODUCT: favorite_product,
        }
