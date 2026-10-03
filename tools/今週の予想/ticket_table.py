"""予想の結果の買い目を、標準出力に出す表にする。"""

from __future__ import annotations

from typing import Any

from 共通.render import Table

from 今週の予想.forecast_tickets import ODDS_NOTE_KNOWN, ODDS_NOTE_UNKNOWN

#: 表の見出し。
HEADERS: tuple[str, ...] = ("買い方", "券種", "買い目", "単位", "期待値", "組の確率", "オッズ", "外した理由")


class TicketTable:
    """1レースの予想の結果の買い目（``ForecastTickets.build`` の並び）を、1点1行の表にする。"""

    def table(self, forecast: dict[str, Any]) -> Table:
        tickets = forecast.get("tickets") or []
        rows = [[ticket["rule"], ticket["ticket_type"], ticket["label"], f"{ticket['stake_units']:g}", _number(ticket["value"]),
                 _percent(ticket["probability"]), _number(ticket["odds"], 1), ticket["dropped"]] for ticket in tickets]
        bought = sum(1 for ticket in tickets if not ticket["dropped"])
        note = (f"買い目 {len(tickets)} 点（買う {bought} 点）。設計書「買うレースと買い目を決める」08 の 2 の印のルール。"
                f"{ODDS_NOTE_KNOWN if forecast.get('odds_known') else ODDS_NOTE_UNKNOWN}。"
                "3連複・3連単の期待値は、市場が見た組の確率 × 3頭の「モデル ÷ 市場」の比（07 の 2）。"
                "トリガミ（どれが当たっても買い方の投資より少なく戻る）とオッズの無い組は「外した理由」に出す。"
                "今の決まりで実際に買うのは複勝だけで、ほかの券種は確かめ中（参考）。")
        return Table(title=f"{forecast['title']} の買い目", columns=list(HEADERS), rows=rows, note=note)


def _number(value: float | None, digits: int = 2) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def _percent(value: float | None) -> str:
    return "" if value is None else f"{value:.1%}"
