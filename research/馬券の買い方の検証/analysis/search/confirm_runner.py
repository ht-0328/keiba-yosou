"""確認: 選んだ戦略だけを確認期間で評価する。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .strategy import Strategy
from .strategy_evaluator import StrategyEvaluator
from .strategy_result import StrategyResult


class ConfirmRunner:
    """探索で選んだ戦略を、確認期間（テスト期間）のレースで、選んだ順のまま評価する。しきい値は探索で決めた値のまま使う。"""

    def __init__(self, evaluator: StrategyEvaluator) -> None:
        self._evaluator = evaluator

    def run(self, strategies: Sequence[Strategy], confirm_races: pd.DataFrame) -> list[StrategyResult]:
        return [self._evaluator.evaluate(strategy, confirm_races) for strategy in strategies]
