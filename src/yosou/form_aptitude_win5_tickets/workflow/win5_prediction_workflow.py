"""WIN5 の日の予測の流れ。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import duckdb

from ..formation import BUDGETS, BudgetTierJudge, BudgetTiers, FavoriteProduct, FormationSearch
from ..leg import LegModelChooser, LegWinPredictor, RaceWinShare
from ..payout import PayoutPool, PoolSizeEstimate
from ..repository import Win5DayRepository, Win5HistoryRepository
from .leg_forecast import LegForecast
from .win5_forecast import Win5Forecast


class Win5PredictionWorkflow:
    """設計書 05 の図2。その日の WIN5 を読み、対象レースごとに使う確率を選んで今のモデルの1着の確率を出してそろえ、
    それより前の WIN5 から発売票数を見積もり、判断用・少なく買う日・多く買う日の予算（と予算の候補）の買い目を1回の探索で組み、
    本命の確率の積を出して、買う（多く）・買う（少なく）・見送り を決める。

    ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。``con`` は元DB への接続（読むだけ）、
    ``predictor`` は今のモデルの予測を包んだもの、``search`` は並べ方と配当の見積もりの式を持った買い目の組み方、
    ``estimator_count`` は配当の見積もりの式に使った当たり組の数（結果に添えるだけ）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, predictor: LegWinPredictor, search: FormationSearch,
                 estimator_count: int = 0, budgets: Sequence[int] = BUDGETS) -> None:
        self._con = con
        self._predictor = predictor
        self._search = search
        self._estimator_count = estimator_count
        self._budgets = tuple(budgets)
        self._chooser = LegModelChooser()
        self._share = RaceWinShare()
        self._pool_size = PoolSizeEstimate()
        self._favorite = FavoriteProduct()
        self._judge = BudgetTierJudge()

    def run(self, race_date: date, tiers: BudgetTiers, line: float) -> Win5Forecast:
        """その日の WIN5 の予測。``tiers`` は段階の予算（判断用・少なく・多くの予算と多く買う日の線）、``line`` は買う日の線（判断用の買い目の日の期待値）。"""
        day = Win5DayRepository(self._con).read(race_date)
        legs = tuple(self._leg(race_id) for race_id in day.race_ids)
        history = Win5HistoryRepository(self._con).read(race_date)
        pool = PayoutPool(self._pool_size.of(history, race_date, day.is_saturday), day.carry)
        tables = [leg.table for leg in legs]
        budgets = sorted({*self._budgets, *tiers.budgets})
        by_budget = self._search.best_by_budget(tables, budgets, pool)
        judge = by_budget[tiers.judge]
        favorite_product = self._favorite.of(tables)
        decision = self._judge.judge(judge.expected_value, line, favorite_product, tiers.favorite_line)
        choice = by_budget[tiers.budget_for(decision)]
        return Win5Forecast(day, legs, pool, self._search.ordering, tiers, line, judge, favorite_product, choice, by_budget, decision,
                            self._estimator_count, datetime.now())

    def _leg(self, race_id: str) -> LegForecast:
        """対象レース1つ: 使う確率を選ぶ → 1着の確率を出す → レースの中でそろえる。"""
        choice = self._chooser.choose(self._con, race_id)
        prediction = self._predictor.predict(self._con, race_id, choice)
        return LegForecast(race_id, choice, self._share.of(prediction))
