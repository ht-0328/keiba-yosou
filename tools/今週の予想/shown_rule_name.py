"""買い方の名前を、そのレースで実際に相手に入れた印に合わせて見せる。"""

from __future__ import annotations

import math
from typing import Any

from 今週の予想.forecast_columns import HORSE_NO, MARK, PLACE_VALUE
from 今週の予想.mark_rule import VALUE_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE


class ShownRuleName:
    """印で組む買い方の名前（``3連単（◎→○▲☆→○▲△☆）`` など）は、☆ を相手に入れる形で書いてある。ところが ☆ を相手に入れるのは
    複勝の期待値が線（``PLACE_VALUE_LINE``。1.25）以上の ☆ だけで、届かない ☆ は表示だけ（``MarkRule``・``MarkTickets``）。
    そのレースで ☆ を入れなかったときは、名前から ☆ を除いて見せ（``3連単（◎→○▲→○▲△）``）、なぜ入れなかったかの1行（``note``）を添える。

    名前は買い方を引く鍵（成績の集計・計画）でもあるので、予想の結果の中の名前は変えず、人に見せるときだけこれで直す。
    ``horses`` は予想の結果の全頭（列 ``mark``・``place_value``・``horse_no``）。無ければ（前の形の予想）名前をそのまま見せる。
    """

    def __init__(self, horses: list[dict[str, Any]] | None) -> None:
        stars = [horse for horse in horses or () if horse.get(MARK) == VALUE_MARK]
        self._known = horses is not None
        self._used = any(_value(horse) >= PLACE_VALUE_LINE for horse in stars)
        self._stars = stars

    def of(self, rule: str) -> str:
        """見せる名前。☆ を相手に入れたレースか、全頭の分からない予想なら、そのまま。"""
        return rule if self._used or not self._known else rule.replace(VALUE_MARK, "")

    def note(self) -> str | None:
        """☆ がいて、相手に入れなかったときの1行。それ以外は None。"""
        if self._used or not self._stars:
            return None
        star = self._stars[0]
        return (f"☆ {int(star[HORSE_NO])} は複勝の期待値 {_value(star):.2f} で線の {PLACE_VALUE_LINE:.2f} に届かないので、"
                f"買い目の相手に入れていない（買い方の名前からも ☆ を除いた）")


def _value(horse: dict[str, Any]) -> float:
    value = horse.get(PLACE_VALUE)
    return float(value) if value is not None and not math.isnan(float(value)) else float("-inf")
