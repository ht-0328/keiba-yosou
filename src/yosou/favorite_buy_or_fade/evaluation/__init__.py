"""評価（設計書 16）。判定した1番人気の結果から、消し・単勝の当たり具合と回収率をまとめる。

| 名前 | 仕事 |
|---|---|
| ``StakePlan`` | 判定ごとの単勝・複勝の掛け金。投資と払戻を出す |
| ``DecisionSummary`` | 判定した1番人気の束を、まとめの1行（消した馬の馬券外率・単勝も買った馬の勝率・回収率）にする |
| ``KindSummary`` | 判定ごとの成績の1行 |
| ``EvaluationTables`` | 年ごと・判定ごと・単位ごとの表を作る |

率の文字の作り方は ``rates.py``。
"""

from .decision_summary import COLUMNS, DecisionSummary
from .evaluation_tables import EvaluationTables
from .kind_summary import KIND_COLUMNS, KindSummary
from .stake_plan import StakePlan

__all__ = ["StakePlan", "DecisionSummary", "KindSummary", "EvaluationTables", "COLUMNS", "KIND_COLUMNS"]
