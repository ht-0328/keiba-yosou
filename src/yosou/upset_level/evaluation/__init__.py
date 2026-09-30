"""この予想だけの、比べる基準と使い方の数え上げ（設計書 16 の 3）。

4クラスの当たり具合を測るクラス（``ClassModelEvaluator``・``ClassMetricCalculator``）は ``yosou.shared.evaluation``。
ここには、この予想だけの基準と、「荒れるレースだけ買う」使い方の線引きの材料を置く。

| クラス | 仕事 |
|---|---|
| ``UserRuleBaseline`` | 利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気 10倍未満）を「中荒れ以上」の予想とみなして、的中率と再現率を出す |
| ``UserRuleResult`` | その値の入れ物 |
| ``FavoriteOddsBaseline`` | 特徴量を1番人気のオッズだけにして同じ手順で学習し、検証データでの当たり具合を出す |
| ``UpsetThresholdSummary`` | 「中荒れ以上の確率」のしきい値ごとに、レース数と実際に中荒れ以上だった割合を数える |
"""

from .favorite_odds_baseline import BASELINE_TIMING, FavoriteOddsBaseline
from .upset_threshold_summary import THRESHOLDS, UpsetThresholdSummary
from .user_rule_baseline import UserRuleBaseline
from .user_rule_result import UserRuleResult

__all__ = [
    "UserRuleBaseline", "UserRuleResult", "FavoriteOddsBaseline", "BASELINE_TIMING",
    "UpsetThresholdSummary", "THRESHOLDS",
]
