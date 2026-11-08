"""買い方の候補と、``predict`` の既定（設計書 16 の 4.）。

既定の並べ方・予算・線は、道具「印の成績」の ``--win5`` で探索期間（2019〜2024年）から決まりどおりに選んだもの
（1着の確率の順・240点・線 1.50。設計書 16 の「結果」）。確認期間（2025年から）では採用の基準に届かなかったので、
設計書 15 の 8 のとおり、予想は毎回出し、日の期待値が線以上の日は楽しむための参加費の財布（ポリシー用）から、この予算で買う。
"""

from .leg_ordering import LegOrdering

#: 試す予算（1回の点数）。予算の候補ごとの表に並べる。
BUDGETS: tuple[int, ...] = (20, 50, 100, 240, 500)
#: 試す買う日の線（日の期待値）。
MIN_VALUES: tuple[float, ...] = (1.00, 1.25, 1.50, 2.00)
#: 試す並べ方。
ORDERINGS: tuple[LegOrdering, ...] = (LegOrdering.BY_EDGE, LegOrdering.BY_PROBABILITY)
#: ``predict`` の既定（探索期間で選んだ買い方）。
DEFAULT_ORDERING = LegOrdering.BY_PROBABILITY
DEFAULT_BUDGET = 240
DEFAULT_MIN_VALUE = 1.50
