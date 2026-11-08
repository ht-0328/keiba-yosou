"""買い方の候補と、``predict`` の既定（設計書 16 の 4.）。

既定の並べ方・予算・線は、道具「印の成績」の ``--win5`` で探索期間（2019〜2024年）から決まりどおりに1つ選んだら、その値に置き換える
（設計書 05 の「今は無く、これから作るところ」の 4）。それまでは、設計書 15 の 5 の「今決めて固定する」例と同じ
1着の確率の順・線 1.00 と、01 の例と同じ予算 100点を仮に使う。
"""

from .leg_ordering import LegOrdering

#: 試す予算（1回の点数）。予算の候補ごとの表に並べる。
BUDGETS: tuple[int, ...] = (20, 50, 100, 240, 500)
#: 試す買う日の線（日の期待値）。
MIN_VALUES: tuple[float, ...] = (1.00, 1.25, 1.50, 2.00)
#: 試す並べ方。
ORDERINGS: tuple[LegOrdering, ...] = (LegOrdering.BY_EDGE, LegOrdering.BY_PROBABILITY)
#: ``predict`` の既定（仮）。
DEFAULT_ORDERING = LegOrdering.BY_PROBABILITY
DEFAULT_BUDGET = 100
DEFAULT_MIN_VALUE = 1.00
