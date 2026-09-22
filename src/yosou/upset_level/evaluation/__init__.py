"""この予想だけの、比べる基準（設計書 16 の 3）。

4クラスの当たり具合を測るクラス（``ClassModelEvaluator``・``ClassMetricCalculator``）は ``yosou.shared.evaluation``。
ここには、利用者の規則を基準として測るクラスを置く。

| クラス | 仕事 |
|---|---|
| ``UserRuleBaseline`` | 利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気 10倍未満）を「中荒れ以上」の予想とみなして、的中率と再現率を出す |
| ``UserRuleResult`` | その値の入れ物 |
"""

from .user_rule_baseline import UserRuleBaseline
from .user_rule_result import UserRuleResult

__all__ = ["UserRuleBaseline", "UserRuleResult"]
