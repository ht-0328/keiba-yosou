"""買い方の候補と、``predict`` の既定（設計書 16 の 4.）。

既定の予算は、利用者が決めた 1回 50点（5,000円。設計書 15 の 5）。並べ方と線は、道具「印の成績」の ``--win5 --win5-budget 50`` で、
探索期間（2019〜2024年）の 50点の買い方の中から決まりどおりに選んだもの（1着の確率の順・50点・線 1.25。設計書 16 の「確かめた結果」）。
採用の基準には届いていないので、設計書 15 の 8 のとおり、予想は毎回出し、日の期待値が線以上の日は楽しむための参加費の財布（ポリシー用）から、
この予算で買う。予算と線はここだけで決まり、``predict``・道具「発走前の通知」・買う計画（道具「今週の予想」）の金額は、すべてこの値から出る。
"""

from .leg_ordering import LegOrdering

#: 試す予算（1回の点数）。予算の候補ごとの表に並べる。
BUDGETS: tuple[int, ...] = (20, 50, 100, 240, 500)
#: 試す買う日の線（日の期待値）。
MIN_VALUES: tuple[float, ...] = (1.00, 1.25, 1.50, 2.00)
#: 試す並べ方。
ORDERINGS: tuple[LegOrdering, ...] = (LegOrdering.BY_EDGE, LegOrdering.BY_PROBABILITY)
#: ``predict`` の既定（利用者が決めた予算 50点の中で、探索期間で選んだ買い方）。
DEFAULT_ORDERING = LegOrdering.BY_PROBABILITY
DEFAULT_BUDGET = 50
DEFAULT_MIN_VALUE = 1.25
