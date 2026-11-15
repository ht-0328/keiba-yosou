"""全レースで出す印の買い目の、1点ごとの購入額の割合と見込みの回収率。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from 今週の予想.equal_payout_stakes import MIN_MULTIPLE, EqualPayoutStakes
from 今週の予想.ticket_rules import MARK_VALUE_LABELS

#: 出す時点（オッズの動きで直した当日の予想で確かめた）。
_RACE_DAY = "当日"


@dataclass(frozen=True)
class MarkReturn:
    """1レースの印の買い目（``MARK_VALUE_LABELS``。トリガミとオッズの無い組は除く）を、どの組が当たっても払った額より多く戻るように配ったもの
    （``EqualPayoutStakes``）。

    ``stakes`` は買い方の名前 → （1点の辞書, 購入額のうちその1点に回す割合）の並び。``multiple`` は当たったときに戻る額の、購入額に対する倍率。
    ``expected`` は見込みの回収率（割合で重みを付けた期待値の和。払戻の見込み ÷ 購入額）。期待値の無い点があれば欠損値。
    ``dropped`` は、全部を払った額より多く戻る形にできず、期待値の低い順に外した点数。
    """

    stakes: dict[str, list[tuple[dict[str, Any], float]]]
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
        stakes = {rule: [(ticket, share) for ticket, share in chosen if ticket["rule"] == rule] for rule in MARK_VALUE_LABELS}
        return cls({rule: pairs for rule, pairs in stakes.items() if pairs}, multiple, expected, len(kept) - len(chosen))

    def heading(self) -> str:
        """例: ``当たれば購入額の 1.35倍（どの組が当たっても同じ）・見込みの回収率 108%。期待値の低い 3点は外した``。"""
        if self.multiple is None:
            return f"なし（どの組を残しても、当たったときに購入額の {MIN_MULTIPLE}倍以上にならない）"
        expected = f"・見込みの回収率 {self.expected * 100:.0f}%" if self.expected is not None else ""
        dropped = f"。全部を買うと払った額より多く戻らないので、期待値の低い {self.dropped}点は外した" if self.dropped else ""
        return f"当たれば購入額の {self.multiple:.2f}倍（どの組が当たっても同じ）{expected}{dropped}"
