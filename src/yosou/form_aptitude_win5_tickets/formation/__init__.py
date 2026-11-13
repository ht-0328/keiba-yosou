"""買い目（設計書 06 の図3、16 の 3.・4.、15 の 13）。

| クラス | 仕事 |
|---|---|
| ``LegOrdering`` | 対象レースの馬を、買い目に入れる順に並べる決まり（列挙。上乗せの順・1着の確率の順） |
| ``Formation`` | フォーメーションを表す値（レースごとに選んだ馬番の並びと、点数） |
| ``ComboGrid`` | フォーメーションの全部の組の、当たる確率と見積もりの配当（5次元の並び） |
| ``FormationValue`` | 全部の組の当たる確率と見積もりの配当を、表の計算でまとめて出す |
| ``FormationChoice`` | 組んだフォーメーションと、買い目のどれかが当たる確率・見積もりの払戻の合計・日の期待値 |
| ``FormationSearch`` | 予算に収まる頭数の並びを全部試し、見積もりの払戻の合計がいちばん大きいフォーメーションを選ぶ（予算の候補ごとにも） |
| ``FavoriteProduct`` | 本命の確率の積（5レースの本命のそろえた1着の確率のかけ算）を出す |
| ``BudgetTiers`` | 段階の予算を表す値（判断用・少なく買う日・多く買う日の予算と、多く買う日の線） |
| ``DayDecision`` | 買う（多く）・買う（少なく）・見送り（列挙） |
| ``BudgetTierJudge`` | 判断用の買い目の日の期待値が買う日の線未満なら「見送り」、以上なら本命の確率の積が線以上で「買う（多く）」、未満で「買う（少なく）」 |

``buying_defaults.py`` は、試す予算・線・並べ方の候補と、``predict`` の既定（判断用の予算・買う日の線・少なく買う日と多く買う日の予算・多く買う日の線）。
"""

from .budget_tier_judge import BudgetTierJudge
from .budget_tiers import BudgetTiers
from .buying_defaults import (
    BUDGETS,
    DEFAULT_MIN_VALUE,
    DEFAULT_ORDERING,
    FAVORITE_PRODUCT_LINE,
    JUDGE_BUDGET,
    LARGE_BUDGET,
    MIN_VALUES,
    ORDERINGS,
    SMALL_BUDGET,
)
from .combo_grid import ComboGrid
from .day_decision import DayDecision
from .favorite_product import FavoriteProduct
from .formation import Formation
from .formation_choice import FormationChoice
from .formation_search import FormationSearch
from .formation_value import FormationValue
from .leg_ordering import LegOrdering

__all__ = [
    "LegOrdering", "Formation", "ComboGrid", "FormationValue", "FormationChoice", "FormationSearch", "FavoriteProduct", "BudgetTiers",
    "DayDecision", "BudgetTierJudge",
    "BUDGETS", "MIN_VALUES", "ORDERINGS", "DEFAULT_ORDERING", "JUDGE_BUDGET", "DEFAULT_MIN_VALUE", "SMALL_BUDGET", "LARGE_BUDGET",
    "FAVORITE_PRODUCT_LINE",
]
