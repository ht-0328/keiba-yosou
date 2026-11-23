"""ばんえいの印の決め方（◎○▲△☆注と無印）。オッズは見ない。

- ◎○▲: 勝つ確率の高い順の 1〜3位。
- △: 4〜6位（3頭まで）。
- ☆・注: 印の無い馬の中で、予想が世間の見立てを上回る度合い（勝つ確率 ÷ 世間の見立て）が 1位・2位の馬。線に届かなければ付けない。
- 残りは無印。危険な人気馬の「消」は、判定を作っていないので付けない。
"""

from __future__ import annotations

from collections.abc import Sequence

#: 勝つ確率の高い順に付ける印。
_RANK_MARKS: tuple[str, ...] = ("◎", "○", "▲", "△", "△", "△")
#: 予想が世間の見立てを上回る馬に付ける印（度合いの大きい順）。
_GAP_MARKS: tuple[str, ...] = ("☆", "注")
#: ☆・注 を付ける度合いの下限。
_MIN_GAP = 1.2
NO_MARK = "－"
TOP_MARK = "◎"


class BaneiMarkRule:
    def assign(self, model: Sequence[float], crowd: Sequence[float]) -> list[tuple[str, str]]:
        """勝つ確率の予想と世間の見立て（同じ並び）から、馬ごとの（印, 印の理由）。理由は ◎・☆・注 だけに書く。"""
        count = len(model)
        marks = [(NO_MARK, "")] * count
        ranked = sorted(range(count), key=lambda index: -model[index])
        for mark, index in zip(_RANK_MARKS, ranked):
            reason = f"勝つ確率がレース内1位（{model[index]:.0%}）" if mark == TOP_MARK else ""
            marks[index] = (mark, reason)
        rest = [index for index in ranked[len(_RANK_MARKS):] if model[index] / crowd[index] >= _MIN_GAP]
        rest.sort(key=lambda index: -model[index] / crowd[index])
        for position, (mark, index) in enumerate(zip(_GAP_MARKS, rest), start=1):
            reason = (f"印の無い馬の中で、予想が世間の見立てを上回る度合いが{position}位"
                      f"（勝つ確率 {model[index]:.1%}・世間の見立て {crowd[index]:.1%}）")
            marks[index] = (mark, reason)
        return marks
