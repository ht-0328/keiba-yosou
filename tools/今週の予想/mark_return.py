"""全レースで出す印の買い目の、1点ごとの金額と見込みの回収率。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from 今週の予想.equal_payout_stakes import MIN_MULTIPLE, EqualPayoutStakes
from 今週の予想.ticket_rules import MARK_VALUE_LABELS

#: 出す時点（オッズの動きで直した当日の予想で確かめた）。
_RACE_DAY = "当日"
#: 1レースに使う額（円）。割合を掛けて 100円単位に丸める。過去のレースで、5,000円から上なら当たったときに払った額を割ることがほぼ無く、
#: 回収率も割合どおりに買ったときとほぼ同じだった（設計書「買うレースと買い目を決める」08 の 2）。
RACE_YEN = 5000
#: 1点の額の単位と最低額（円）。
YEN_UNIT = 100
#: 買うと判断する見込みの回収率の線（これ未満は見送り）。過去のレースで、見込みが線以上のレースだけ買うと回収率が上がった。
BUY_LINE = 1.0


@dataclass(frozen=True)
class MarkReturn:
    """1レースの印の買い目（``MARK_VALUE_LABELS``。トリガミとオッズの無い組は除く）を、どの組が当たっても払った額より多く戻るように配ったもの
    （``EqualPayoutStakes``）と、1レース ``RACE_YEN`` 円を割合で分けた1点ごとの金額（100円単位。100円に届かない組は 100円）。

    ``stakes`` は買い方の名前 → （1点の辞書, 割合, 金額）の並び。``multiple`` は割合どおりに買って当たったときの、購入額に対する倍率。
    ``expected`` は見込みの回収率（割合で重みを付けた期待値の和）。期待値の無い点があれば欠損値。
    ``dropped`` は、全部を払った額より多く戻る形にできず、期待値の低い順に外した点数。
    """

    stakes: dict[str, list[tuple[dict[str, Any], float, int]]]
    multiple: float | None
    expected: float | None
    dropped: int

    @classmethod
    def of(cls, forecast: dict[str, Any]) -> MarkReturn | None:
        """当日の予想の印の買い目。当日でないか、買い目が無ければ None。"""
        if forecast.get("timing") != _RACE_DAY:
            return None
        kept = [ticket for ticket in forecast.get("tickets", []) if ticket.get("rule") in MARK_VALUE_LABELS and not ticket.get("dropped")]
        if not kept:
            return None
        chosen, multiple = EqualPayoutStakes().allocate(kept)
        values = [share * ticket["value"] for ticket, share in chosen if isinstance(ticket.get("value"), (int, float))]
        expected = sum(values) if chosen and len(values) == len(chosen) else None
        stakes = {rule: [(ticket, share, _yen(share)) for ticket, share in chosen if ticket["rule"] == rule] for rule in MARK_VALUE_LABELS}
        return cls({rule: rows for rule, rows in stakes.items() if rows}, multiple, expected, len(kept) - len(chosen))

    @property
    def buys(self) -> bool:
        """買うか（見込みの回収率が線以上）。"""
        return self.expected is not None and self.expected >= BUY_LINE

    @property
    def total_yen(self) -> int:
        return sum(yen for rows in self.stakes.values() for _, _, yen in rows)

    @property
    def least_return_yen(self) -> int:
        """どれか1つが当たったときに戻る額のうち、いちばん少ないもの（100円単位に丸めたあとの金額で。100円未満は切り下げ）。"""
        least = min((yen * ticket["odds"] for rows in self.stakes.values() for ticket, _, yen in rows), default=0)
        return int(least // YEN_UNIT) * YEN_UNIT

    def heading(self) -> str:
        """例: ``買う（見込みの回収率 116%）。合計 5,300円で、どれが当たっても 10,100円以上戻る``。"""
        if self.multiple is None:
            return f"なし（どの組を残しても、当たったときに購入額の {MIN_MULTIPLE}倍以上にならない）"
        if self.expected is None:
            judge = "見送り（見込みの回収率を出せない）"
        else:
            expected = f"見込みの回収率 {self.expected * 100:.0f}%"
            judge = f"買う（{expected}）" if self.buys else f"見送り（{expected}。100% 未満）"
        dropped = f"。全部を買うと払った額より多く戻らないので、期待値の低い {self.dropped}点は外した" if self.dropped else ""
        return f"{judge}。合計 {self.total_yen:,}円で、どれが当たっても {self.least_return_yen:,}円以上戻る{dropped}"


def _yen(share: float) -> int:
    """1レースの額に割合を掛けて 100円単位に四捨五入した額（100円に届かなければ 100円）。"""
    return max(YEN_UNIT, int(RACE_YEN * share / YEN_UNIT + 0.5) * YEN_UNIT)
