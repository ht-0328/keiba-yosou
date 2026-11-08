"""WIN5 のフォーメーションの文字（``3,5,10/6,8/2,5/4/4,10,11,15``）と、レースごとの馬番の並びを行き来する。

買い目の記録（回顧の表1）の「買い目」の列に、1日1行で WIN5 の買い目を書くための形。レースの順（発売の順）に「/」で区切り、
1つのレースの中の馬番は「,」で区切って小さい順に並べる。
"""

from __future__ import annotations

from collections.abc import Sequence

#: レースの区切りと、馬番の区切り。
LEG_SEPARATOR, HORSE_SEPARATOR = "/", ","


def combo_text(legs: Sequence[Sequence[int]]) -> str:
    """レースごとの馬番の並び → フォーメーションの文字。"""
    return LEG_SEPARATOR.join(HORSE_SEPARATOR.join(str(number) for number in sorted(int(n) for n in picks)) for picks in legs)


def combo_legs(text: str) -> tuple[tuple[int, ...], ...]:
    """フォーメーションの文字 → レースごとの馬番の並び。"""
    return tuple(tuple(int(number) for number in leg.split(HORSE_SEPARATOR)) for leg in str(text).split(LEG_SEPARATOR))
