"""1日の WIN5 を買うか見送るかの、まとめと通知に書く形。"""

from __future__ import annotations

from dataclasses import dataclass

from 今週の予想.win5_plan import Win5Plan
from 今週の予想.win5_record import Win5Record


@dataclass(frozen=True)
class Win5Decision:
    """予想の記録（``Win5Record``）と買う計画（``Win5Plan``）から決まる、買うか（``buys``）とその理由（``reason``）。

    計画があり、記録と同じ買い目なら計画に従う（財布の残高が足りずに買わないこともある）。計画が無い（予想のあとに計画をまだ決め直して
    いない）か、記録と買い目が合わない（前の予想の計画）なら、予想の判断（日の期待値が線以上か）に従う。
    """

    buys: bool
    reason: str

    @classmethod
    def of(cls, record: Win5Record, plan: Win5Plan | None) -> Win5Decision:
        if plan is not None and plan.formation == record.formation:
            return cls(plan.buys, plan.reason)
        return cls(record.buys, record.value_text())

    @property
    def label(self) -> str:
        return "買う" if self.buys else "見送り"
