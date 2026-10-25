"""◎ の単勝の期待値が線（1.00）以上か未満かを決める。"""

from __future__ import annotations

import math

#: 線（固定）。◎ の単勝の期待値がこれ以上なら、モデルは単勝を買って得と見ている。
LINE = 1.0
#: 線以上・線未満の2つの帯（表に出す並び）。買い方の決まりで「◎の期待値 1.00 以上のレース」と書くときの値。
HIGH, LOW = f"{LINE:.2f} 以上", f"{LINE:.2f} 未満"
WIN_VALUE_BANDS: tuple[str, ...] = (HIGH, LOW)


class WinValueBand:
    """レースの ◎（単勝の期待値がいちばん高い馬）の単勝の期待値が、線（1.00）以上か未満かを決める（設計書「近走と適性から3着以内を予想」の 16 の 6）。

    - 1.00 以上: モデルは単勝を買って得と見ている。当日の予想では、このレースの単勝・馬単などを買う対象になる（買うレースと買い目を決める の 08 の 2）。
    - 1.00 未満: モデル自身が損と見ている。◎ は付くが、この条件の買い目は買わない。
    期待値が無い（木曜。オッズが無い）なら None。線は固定で、検証データでは決めない（半年の検証期間で線を選ぶと、区切りごとに大きくばらついた）。
    """

    def of(self, value: float | None) -> str | None:
        if value is None or math.isnan(value):
            return None
        return HIGH if value >= LINE else LOW
