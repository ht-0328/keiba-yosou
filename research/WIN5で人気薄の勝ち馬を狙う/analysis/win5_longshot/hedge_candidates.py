"""比べる抑えの候補と、本線の決まり（今の買い目そのまま）。"""

from __future__ import annotations

from itertools import product

from yosou.form_aptitude_win5_tickets.formation import DEFAULT_BUDGET, DEFAULT_MIN_VALUE

from .hedge_candidate import BY_MARKET, BY_SHARE, CURRENT, NEW, HedgeCandidate

#: 本線（今の買い目。予想「近走と適性からWIN5の買い目を決める」の既定: 1着の確率の順・50点・線 1.25）。
MAIN_BUDGET = DEFAULT_BUDGET
MAIN_LINE = DEFAULT_MIN_VALUE
#: 抑えの組の名前。
NEW_HEDGE = "抑え（人気薄の1着の予想）"
RULE_HEDGE = "抑え（決まり: 人気の順）"
#: 候補の広げ方。
UPSET_COUNTS: tuple[int, ...] = (1, 2)
LONGSHOTS: tuple[int, ...] = (2, 3, 4)
BUDGETS: tuple[int, ...] = (10, 20, 30)
LINES: tuple[float | None, ...] = (None, 1.00)

#: 全部の候補。人気薄の1着の予想の順（新しい確率）と、比べる決まり（人気の順。今のモデルの確率）。
CANDIDATES: tuple[HedgeCandidate, ...] = tuple(
    HedgeCandidate(group, source, order, upset, longshots, budget, line)
    for (group, source, order), upset, longshots, budget, line in product(
        ((NEW_HEDGE, NEW, BY_SHARE), (RULE_HEDGE, CURRENT, BY_MARKET)), UPSET_COUNTS, LONGSHOTS, BUDGETS, LINES)
)
