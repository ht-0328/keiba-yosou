"""6つの印。"""

from __future__ import annotations

from enum import Enum


class Mark(Enum):
    """予想の印（設計書 16 の 8.）。値は表に出す記号で、印を付けた表の ``mark`` の列にもそのまま入れる。

    ◎○▲△ は 1着の確率の 1〜4位（買い方に使う）。☆ は 5位以下で単勝の期待値がいちばん高い馬（1.0 以上のときだけ）、
    注 は印の無い馬で先頭の確率がいちばん高い馬（どちらも表示だけ）。
    """

    FIRST = "◎"
    SECOND = "○"
    THIRD = "▲"
    FOURTH = "△"
    VALUE = "☆"
    LEADER = "注"

    @property
    def label(self) -> str:
        """表に出す記号。"""
        return self.value


#: 順位で付ける印（1位から順）。
RANK_MARKS: tuple[Mark, ...] = (Mark.FIRST, Mark.SECOND, Mark.THIRD, Mark.FOURTH)
