"""買い目（設計書 06 の図3、16 の 3.・4.）。

| クラス | 仕事 |
|---|---|
| ``LegOrdering`` | 対象レースの馬を、買い目に入れる順に並べる決まり（列挙。上乗せの順・1着の確率の順） |
| ``Formation`` | フォーメーションを表す値（レースごとに選んだ馬番の並びと、点数） |
| ``ComboGrid`` | フォーメーションの全部の組の、当たる確率と見積もりの配当（5次元の並び） |
| ``FormationValue`` | 全部の組の当たる確率と見積もりの配当を、表の計算でまとめて出す |
| ``FormationChoice`` | 組んだフォーメーションと、買い目のどれかが当たる確率・見積もりの払戻の合計・日の期待値 |
| ``FormationSearch`` | 予算に収まる頭数の並びを全部試し、見積もりの払戻の合計がいちばん大きいフォーメーションを選ぶ（予算の候補ごとにも） |
| ``DayDecision`` | 買う か 見送り（列挙） |
| ``DayBuyJudge`` | 日の期待値が買う日の線以上なら「買う」、未満なら「見送り」 |

``buying_defaults.py`` は、試す予算・線・並べ方の候補と、``predict`` の既定。
"""

from .buying_defaults import BUDGETS, DEFAULT_BUDGET, DEFAULT_MIN_VALUE, DEFAULT_ORDERING, MIN_VALUES, ORDERINGS
from .combo_grid import ComboGrid
from .day_buy_judge import DayBuyJudge
from .day_decision import DayDecision
from .formation import Formation
from .formation_choice import FormationChoice
from .formation_search import FormationSearch
from .formation_value import FormationValue
from .leg_ordering import LegOrdering

__all__ = [
    "LegOrdering", "Formation", "ComboGrid", "FormationValue", "FormationChoice", "FormationSearch", "DayDecision", "DayBuyJudge",
    "BUDGETS", "MIN_VALUES", "ORDERINGS", "DEFAULT_ORDERING", "DEFAULT_BUDGET", "DEFAULT_MIN_VALUE",
]
