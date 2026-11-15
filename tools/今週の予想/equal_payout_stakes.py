"""どの組が当たっても同じ額が戻るように、1点ごとの購入額の割合を決める。"""

from __future__ import annotations

from typing import Any

#: 当たったときに戻る額の、購入額に対する倍率の下限。締め切りまでにオッズが少し下がっても、払った額より多く戻るように 1.1 倍にする。
MIN_MULTIPLE = 1.1


class EqualPayoutStakes:
    """買い目（1点の辞書。``odds``・``value``）を、どの組が当たっても同じ額が戻るように配る。

    1点の割合 = (1 ÷ オッズ) ÷ Σ(1 ÷ オッズ)。当たれば、購入額 ÷ Σ(1 ÷ オッズ) が戻る（購入額の 1 ÷ Σ(1 ÷ オッズ) 倍）。
    この倍率が ``MIN_MULTIPLE`` に届かなければ、期待値の低い組（期待値が無ければいちばん低い扱い）から1点ずつ外して、届いたところで止める。
    オッズの無い組は買わない。戻り値は（残した組と割合の並び（期待値の高い順）, 倍率）。残せる組が無ければ（空, None）。
    例: オッズ 4倍・10倍・20倍の3点なら、Σ = 0.25 + 0.1 + 0.05 = 0.4 で、割合は 62.5%・25%・12.5%、当たれば購入額の 2.5 倍。
    """

    def allocate(self, tickets: list[dict[str, Any]]) -> tuple[list[tuple[dict[str, Any], float]], float | None]:
        priced = [ticket for ticket in tickets if isinstance(ticket.get("odds"), (int, float)) and ticket["odds"] > 1.0]
        kept = sorted(priced, key=lambda ticket: -(ticket["value"] if isinstance(ticket.get("value"), (int, float)) else float("-inf")))
        while kept:
            total = sum(1.0 / ticket["odds"] for ticket in kept)
            if 1.0 / total >= MIN_MULTIPLE:
                return [(ticket, (1.0 / ticket["odds"]) / total) for ticket in kept], 1.0 / total
            kept.pop()
        return [], None
