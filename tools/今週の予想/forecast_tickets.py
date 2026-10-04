"""1レースの印から、買い目を組んで締め切り前のオッズを付ける。"""

from __future__ import annotations

from typing import Any

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboExpectedValue
from yosou.shared.repository import AnnouncedTicketOddsRepository

from 今週の予想.forecast_columns import EXPECTATION
from 今週の予想.mark_tickets import ODDS, RULE, VALUE, MarkTickets
from 今週の予想.torigami_filter import DROPPED, TorigamiFilter

#: 結果の辞書の鍵（買い目1点）。
TICKET_KEYS: tuple[str, ...] = ("rule", "ticket_type", "combo", "horses", "label", "stake_units", "value", "probability", "odds", "dropped")
#: 結果の辞書に入れる、買い目のオッズの時刻の説明。
ODDS_NOTE_KNOWN = "締め切り前のオッズ（取り込んだ時点のもの）"
ODDS_NOTE_UNKNOWN = "オッズが無いので、期待値とトリガミは出ない"


class ForecastTickets:
    """印を付けた1レースの表（``MarkRule.assign`` の戻り値）から、印のルールの買い目（``MarkTickets``。設計書「買うレースと買い目を決める」08 の 2）を組み、
    締め切り前のオッズ（``AnnouncedTicketOddsRepository``）で組の確率とトリガミ（``TorigamiFilter``）を付けて、JSON にできる辞書の並びにする。

    オッズの無い時点（木曜）は、買い目は組むがオッズ・期待値・トリガミは付かない（複勝と、期待値で絞る3連単・3連複は0点になる）。
    1点は ``TICKET_KEYS`` の鍵を持つ。``combo`` は組番（馬番を2桁ずつ）、``horses`` は馬番の並び、``label`` は人が読む並び
    （着順を区別する券種は ``3→1→8``、順不同は ``1-3-8``）、``dropped`` は外した理由（空なら買う）。
    """

    def __init__(self) -> None:
        self._tickets = MarkTickets()
        self._value = ComboExpectedValue()
        self._torigami = TorigamiFilter()

    def build(self, con: duckdb.DuckDBPyConnection, race_id: str, marked: pd.DataFrame, expectation: str | None,
              odds_known: bool) -> list[dict[str, Any]]:
        race = marked.assign(race_id=race_id, race_date=pd.Timestamp(f"{race_id[:4]}-{race_id[4:6]}-{race_id[6:8]}"), fold="",
                             **{EXPECTATION: expectation})
        tickets = self._tickets.build(race)
        if tickets.empty:
            return []
        if odds_known:
            tickets[ODDS] = self._odds(con, race_id, tickets)
            tickets = self._torigami.apply(tickets)
        else:
            tickets[ODDS] = np.nan
            tickets[DROPPED] = ""
        tickets["probability"] = self._value.probability(tickets[VALUE], tickets[ODDS])
        return [self._row(ticket) for _, ticket in tickets.iterrows()]

    def _odds(self, con: duckdb.DuckDBPyConnection, race_id: str, tickets: pd.DataFrame) -> pd.Series:
        """券種ごとに締め切り前のオッズを読み、組番で引く。"""
        odds = pd.Series(np.nan, index=tickets.index)
        for label, group in tickets.groupby("ticket_type", sort=False):
            board = AnnouncedTicketOddsRepository(con, TicketType.parse(label)).read(race_id)
            lookup = dict(zip(board["combo"].astype(str), board["odds"].astype(float), strict=True))
            odds.loc[group.index] = group["combo"].map(lookup)
        return odds

    def _row(self, ticket: pd.Series) -> dict[str, Any]:
        ticket_type = TicketType.parse(ticket["ticket_type"])
        combo = str(ticket["combo"])
        horses = [int(combo[at:at + 2]) for at in range(0, len(combo), 2)]
        joiner = "→" if ticket_type.spec.is_ordered else "-"
        return {
            "rule": ticket[RULE], "ticket_type": ticket_type.label, "combo": combo, "horses": horses, "label": joiner.join(map(str, horses)),
            "stake_units": float(ticket["stake_units"]), "value": _plain(ticket[VALUE]), "probability": _plain(ticket["probability"]),
            "odds": _plain(ticket[ODDS]), "dropped": str(ticket[DROPPED]),
        }


def _plain(value: Any) -> float | None:
    """欠損値は None、ほかは Python の float（JSON のため）。"""
    return None if value is None or pd.isna(value) else float(value)
