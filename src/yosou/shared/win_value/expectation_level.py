"""レースの期待度（高・低）を決める。"""

from __future__ import annotations

import math

#: 期待度の2段階（表に出す並び）。
HIGH, LOW = "高", "低"
EXPECTATION_LEVELS: tuple[str, ...] = (HIGH, LOW)
#: 高と低を分ける線（固定）。◎ の単勝の期待値がこれ以上なら、モデルは単勝を買って得と見ている。
LINE = 1.0


class ExpectationLevel:
    """レースの期待度を、◎（単勝の期待値がいちばん高い馬）の単勝の期待値から決める（設計書「近走と適性から3着以内を予想」の 16 の 6）。

    - 高: 期待値が 1.00 以上（モデルは単勝を買って得と見ている）。
    - 低: 期待値が 1.00 未満。
    期待値が無い（木曜。オッズが無い）なら None。線は固定で、検証データでは決めない（半年の検証期間で線を選ぶと、区切りごとに大きくばらついた）。
    """

    def of(self, value: float | None) -> str | None:
        if value is None or math.isnan(value):
            return None
        return HIGH if value >= LINE else LOW
