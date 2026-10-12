"""この研究の決まり（払戻の段、理論を作る年と確かめる年、人気薄）。docs/01 の 3 と 7。

帯・荒れたレースの線と1レースの予算は、本番の予想（``yosou.upset_premise``）と同じものを使う（2か所に書かないため）。
"""

from __future__ import annotations

from yosou.upset_premise.dataset import OBI_YEN, WILD_LINE_YEN

#: 大荒れ = 3連単の払戻（100円あたり）が 10万円以上（本番の「荒れたレース」の線と同じ）。
BIG_YEN = WILD_LINE_YEN

#: 払戻の段の名前（3連単の払戻で分ける）。
OBI, BIG, OTHER = "帯", "大荒れ", "それ以外"

#: 理論を作る年（この年までしか見ない）と、確かめる年（まだ見ていない年）、参考に並べる年。
THEORY_LAST_YEAR = 2020
CHECK_YEARS: tuple[int, ...] = (2021, 2022)
REFERENCE_FIRST_YEAR = 2023

#: 人気薄 = 単勝6番人気以下（ルール集の言葉に合わせる）。
LONGSHOT_FROM_POPULARITY = 6


def payout_class(trifecta_yen: float) -> str:
    """3連単の払戻（100円あたり）から、払戻の段（帯・大荒れ・それ以外）を決める。"""
    if trifecta_yen >= OBI_YEN:
        return OBI
    if trifecta_yen >= BIG_YEN:
        return BIG
    return OTHER
