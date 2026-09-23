"""しきい値の格子で戦略を回し、採否の基準で絞り、テスト期間で確かめる。

| クラス | 仕事 |
|---|---|
| ``Strategy`` | 戦略1つ（参加パターン・しきい値・広め/少点数の買い方）。名前と JSON の往復 |
| ``StrategyGrid`` | 参加パターンごとに要る軸だけを回して、戦略の並びを作る。荒れ度の線は探索期間の分位で決める |
| ``StrategyEvaluator`` | 1つの戦略を、材料表のレースと精算表で評価する（全体・広め・少点数・月別の回収率） |
| ``StrategyResult`` | 評価の結果（対象・買ったレース数・回収率のまとめ） |
| ``AdoptionRule`` | 採否の基準（事前に固定。docs/03-protocol.md） |
| ``SearchRunner`` | 格子の全戦略を評価し、回収率の順に並べ、採用候補を選ぶ |
| ``ConfirmRunner`` | 選んだ戦略だけを、確認期間で評価する |
| ``ChosenStrategiesFile`` | 選んだ戦略の JSON の読み書き |

格子の値は ``threshold_grid.py``。
"""

from .adoption_rule import AdoptionRule
from .chosen_strategies_file import ChosenStrategiesFile
from .confirm_runner import ConfirmRunner
from .search_runner import SearchRunner
from .strategy import Strategy
from .strategy_evaluator import StrategyEvaluator
from .strategy_grid import StrategyGrid
from .strategy_result import StrategyResult
from .threshold_grid import CHOSEN_LIMIT, DANGER_THRESHOLDS, FORM_THRESHOLDS, TOP_KS, UPSET_TOP_SHARES

__all__ = [
    "Strategy", "StrategyGrid", "StrategyEvaluator", "StrategyResult", "AdoptionRule", "SearchRunner", "ConfirmRunner",
    "ChosenStrategiesFile", "UPSET_TOP_SHARES", "FORM_THRESHOLDS", "DANGER_THRESHOLDS", "TOP_KS", "CHOSEN_LIMIT",
]
