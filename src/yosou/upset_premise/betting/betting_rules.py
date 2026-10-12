"""買い目の決まり（1レースの予算・1点の金額の単位と上限・一律の買い方の線。定数だけ）。設計書 15 の 1・4・6。"""

from __future__ import annotations

from ..dataset import WILD_LINE_YEN

#: 1レースの予算（利用者の指定）。
RACE_BUDGET_YEN = 10_000
#: 1点の金額の単位と上限。上限の 1,000円は、帯に 1,000倍の組が要ることになる線。
STAKE_UNIT_YEN = 100
STAKE_MAX_YEN = 1_000
#: 一律の買い方で買う組のオッズの下限（1,000倍）。荒れたレースの線（3連単の払戻 10万円）を 100円あたりの倍率にしたもの。
BIG_ODDS = WILD_LINE_YEN // STAKE_UNIT_YEN
#: 一律の買い方の1点の金額の3パターン（100円 = 100点・300円 = 33点・500円 = 20点。利用者の指定）と、その既定。
FLAT_STAKE_CHOICES: tuple[int, ...] = (100, 300, 500)
DEFAULT_FLAT_STAKE_YEN = 100
