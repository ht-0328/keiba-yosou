"""1日の WIN5 を買うか見送るかの、まとめと通知に書く形。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_win5_tickets.formation import DayDecision

from 今週の予想.win5_plan import Win5Plan
from 今週の予想.win5_record import Win5Record


@dataclass(frozen=True)
class Win5Decision:
    """予想の記録（``Win5Record``）と買う計画（``Win5Plan``）から決まる、買うか（``buys``）と、見せる判断の名前（``label``。
    ``買う（多く）``・``買う（少なく）``・``見送り``）と、その理由（``reason``）。

    計画があり、記録と同じ買い目なら計画に従う（財布の残高が足りずに買わないこともある）。計画が無い（予想のあとに計画をまだ決め直して
    いない）か、記録と買い目が合わない（前の予想の計画）なら、予想の判断（判断用の買い目の日の期待値が線以上か。買う日は本命の確率の積で
    多く・少なく）に従う。
    """

    buys: bool
    label: str
    reason: str

    @classmethod
    def of(cls, record: Win5Record, plan: Win5Plan | None) -> Win5Decision:
        if plan is not None and plan.formation == record.formation:
            buys, reason = plan.buys, plan.reason
        else:
            buys, reason = record.buys, record.reason_text()
        return cls(buys, record.decision if buys else DayDecision.SKIP.label, reason)
