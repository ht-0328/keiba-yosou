"""買い目の決まり（1レースの予算・1点の金額の単位と上限。定数だけ）。設計書 15 の 1・4。"""

from __future__ import annotations

#: 1レースの予算（利用者の指定）。
RACE_BUDGET_YEN = 10_000
#: 1点の金額の単位と上限。上限の 1,000円は、帯に 1,000倍の組が要ることになる線。
STAKE_UNIT_YEN = 100
STAKE_MAX_YEN = 1_000
