"""保存してある WIN5 の予想の記録から、通知の文を作る（財布で買うかは、その場で決める）。"""

from __future__ import annotations

from datetime import date

from 今週の予想.win5_decision import Win5Decision
from 今週の予想.win5_plan import POLICY_NOTE, Win5Plan
from 今週の予想.win5_planner import Win5Planner
from 今週の予想.win5_record import Win5Record
from 今週の予想.win5_record_store import Win5RecordStore

from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.win5_slot import Win5Slot


class Win5Message:
    """文はレースの通知と同じ短い形で、見出し・判断（買う（多く）／買う（少なく）／見送り と、その理由の1行: 判断用の買い目の日の期待値と線、
    本命の確率の積と多く買う日の線、買う予算）・買い目（点数と金額、レースごとの選んだ馬番と馬名）・当たる確率とキャリーオーバー・
    「楽しむ用の財布で」の1行。表の画像は付けない（全頭の確率は予想の記録と開催日のまとめの WIN5 の節にある）。

    予想の記録は予想のパッケージの predict が書いたもの（``Win5RecordStore``）。買うかどうかは、買う計画と同じ決まり（``Win5Planner``。
    ポリシー用の財布のその日より前の残高が代金に足りなければ見送り）でその場で決め、``Win5Decision`` で文にする（``planner`` が無ければ予想の判断）。
    計画そのもの（plan.json・回顧の表1）は、このあとのレースの予想で forecast.py が書き直す。
    """

    def __init__(self, records: Win5RecordStore | None = None, planner: Win5Planner | None = None) -> None:
        self._records = records or Win5RecordStore()
        self._planner = planner

    def build(self, slot: Win5Slot) -> RaceNotice:
        day = date.fromisoformat(slot.day)
        record = self._records.load(day)
        if record is None:
            raise LookupError(f"{slot.day} の WIN5 の予想の記録がありません")
        plan = self._planner.plan(record, day) if self._planner is not None else None
        return RaceNotice(self.describe(record, plan, slot))

    def describe(self, record: Win5Record, plan: Win5Plan | None, slot: Win5Slot) -> str:
        decision = Win5Decision.of(record, plan)
        money = f"{record.points}点 {record.stake:,}円"
        heading = f"買い目（{money}・ポリシー用の財布から）:" if decision.buys else f"買い目（参考。買わない。{money}）:"
        legs = [f"- {number} {leg.label}: {leg.pick_text()}" for number, leg in enumerate(record.legs, start=1)]
        return "\n".join([
            f"**{slot.label}** 中央の予想",
            f"判断: **{decision.label}**（{decision.reason}）",
            heading, *legs,
            f"当たる確率 {record.hit_probability:.1%}・日の期待値 {record.expected_value:.2f}・キャリーオーバー {record.carry_text()}",
            POLICY_NOTE,
        ])
