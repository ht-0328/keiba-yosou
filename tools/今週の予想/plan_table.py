"""買うレースの計画を標準出力の表にする。"""

from __future__ import annotations

from datetime import date
from typing import Any

from 共通.render import Table

from 今週の予想.race_plan import NO_BET, RacePlan

#: 表の列。
COLUMNS: list[str] = ["レース", "時点", "参加の種類", "E（単位）", "M", "買い目（複勝）", "買い目（単勝・馬単・組の期待値）", "金額（円）", "理由"]


class PlanTable:
    """1開催日の計画の表（買うレースを先に、買わないレースをあとに）。注記に財布の残高と予算を書く。"""

    def table(self, day: date, plans: list[RacePlan], wallet: dict[str, Any]) -> Table:
        ordered = sorted(plans, key=lambda plan: (not plan.buys, plan.kind == NO_BET, -plan.profit_units))
        rows = []
        for plan in ordered:
            picks = "・".join(f"{pick.horse_no}（{pick.value:.2f}）" if pick.value is not None else str(pick.horse_no) for pick in plan.picks)
            tickets = "・".join(f"{ticket.ticket_type} {ticket.label} {ticket.yen:,}円" for ticket in plan.tickets)
            reason = "。".join(part for part in (plan.reason, plan.ticket_reason) if part)
            rows.append([plan.title, plan.timing, plan.kind, f"{plan.profit_units:.2f}", f"{plan.max_value:.2f}" if plan.max_value is not None else "",
                         picks, tickets, f"{plan.stake_yen:,}" if plan.stake_yen else "", reason])
        total = sum(plan.stake_yen for plan in plans)
        points = wallet["単勝・馬単の1点"]
        combo_points = wallet.get("組の期待値の1点", {})
        combo_note = ("組の期待値の1点: " + "・".join(f"{label} {yen:,}円" for label, yen in combo_points.items()) + "（0円の券種は買わない）。"
                      if combo_points else "")
        note = (f"財布（月初の残高）: 勝負用 {wallet['勝負用']:,}円・ポリシー用 {wallet['ポリシー用']:,}円・単勝・馬単用 {wallet['単勝・馬単用']:,}円"
                f"・組の期待値用 {wallet.get('組の期待値用', 0):,}円。"
                f"1レースの予算: 勝負 {wallet['予算']['勝負']:,}円"
                f"（1点 {wallet['1点']:,}円）・ノルマ（重賞）{wallet['予算']['ノルマ（重賞）']:,}円・ノルマ（日）{wallet['予算']['ノルマ（日）']:,}円。"
                f"単勝・馬単の1点: 単勝 {points['単勝']:,}円・馬単 {points['馬単']:,}円（0円の券種は 100円に届かないので買わない）。{combo_note}"
                f"この日の合計 {total:,}円。E は複勝（期待値 1.25 以上）の Σ（期待値 − 1）、M は最大の複勝の期待値。"
                "単勝・馬単は、当日の予想の単勝（期待値）と、◎の単勝の期待値が 1.00 以上のレースの ◎ の馬単（◎→○▲☆）。"
                "組の期待値は、当日の予想で、組の期待値が線以上の馬単・ワイド・3連複・3連単（決まりは設計書 08 の 2）。"
                "計画は reports/今週の予想/<日>/plan.json と回顧の表1「買い目の記録」に書く（レースが終わると払戻が入る）")
        return Table(COLUMNS, rows, title=f"買うレース: {day}", note=note)
