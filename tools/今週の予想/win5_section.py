"""開催日のまとめの「WIN5」の節（その日の WIN5 の買い目と、買うか見送りか）。"""

from __future__ import annotations

from 共通.render import Table, to_markdown

from 今週の予想.win5_decision import Win5Decision
from 今週の予想.win5_plan import POLICY_NOTE, Win5Plan
from 今週の予想.win5_record import Win5Record

#: 対象レースの表の列。
COLUMNS: list[str] = ["何レース目", "レース", "使った確率", "頭数", "選んだ馬"]


class Win5Section:
    """WIN5 の予想の記録（``Win5Record``）と、買う計画（``Win5Plan``。``plan.json`` の ``win5``）から、まとめの節の行と見出しの1行を作る。
    買うかどうかは ``Win5Decision`` で決める。"""

    def lines(self, record: Win5Record, plan: Win5Plan | None) -> list[str]:
        decision = Win5Decision.of(record, plan)
        money = f"{record.points}点 {record.stake:,}円" + ("（ポリシー用の財布から）" if decision.buys else "（参考。買わない）")
        return [
            "## WIN5", "",
            f"- 判断: **{decision.label}**（{decision.reason}）。予想した時刻 {record.made_at[:16].replace('T', ' ')}",
            f"- 買い目: {money}",
            f"- 買い目のどれかが当たる確率 {record.hit_probability:.1%}・日の期待値 {record.expected_value:.2f}・キャリーオーバー {record.carry_text()}",
            f"- {POLICY_NOTE}",
            "", to_markdown(self._legs(record)), "",
        ]

    def head_line(self, record: Win5Record, plan: Win5Plan | None) -> str:
        """まとめの見出しの箇条書きに足す1行。"""
        return f"- WIN5: {Win5Decision.of(record, plan).label}・{record.points}点 {record.stake:,}円（下の「WIN5」の節）"

    @staticmethod
    def _legs(record: Win5Record) -> Table:
        rows = [[f"{number}", leg.label, leg.model, len(leg.picks), leg.pick_text()] for number, leg in enumerate(record.legs, start=1)]
        return Table(COLUMNS, rows)
