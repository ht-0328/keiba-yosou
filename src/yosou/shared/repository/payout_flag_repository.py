"""払戻の親（hr）のフラグを、期間ぶん読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from ..betting import TicketType
from .race_day_range import RaceDayRange

#: 払戻の親の表と、そのデータ区分（1 速報成績（払戻確定）・2 成績（月曜））。オッズの 4・5 とは別の意味。
_HEADER_TABLE = "hr"
_PAYOUT_STAGES: tuple[str, ...] = ("1", "2")
#: フラグの列名は「不成立フラグ　単勝」のように全角スペースで券種の名前をつなぐ（JV-Data の列名のまま）。
_VOID_KINDS: tuple[str, ...] = ("不成立フラグ", "特払フラグ")
_REFUND_FLAG = "返還フラグ　単勝"
_SEPARATOR = "　"
_ON = "1"
#: 出力の列。券種ごとの ``<key>_void``（不成立か特払なら True）と、``refunded``（返還があったなら True）。
REFUNDED = "refunded"


def void_column(ticket_type: TicketType) -> str:
    """その券種が成立しなかったか（不成立か特払）の列の名前。"""
    return f"{ticket_type.key}_void"


class PayoutFlagRepository:
    """払戻の親（``hr``）から、7券種の不成立・特払と、返還の有無を、期間の全レースぶん 1レース1行で読む。

    不成立・特払の券種は、そのレースで賭けない（見送り。使う側の精算のクラスが落とす）。返還はレースが成立して払戻もあるので、数を報告するだけ
    （荒れ具合の設計書 10 と同じ扱い）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, days: RaceDayRange) -> pd.DataFrame:
        flag_names = [self._flag_name(kind, ticket_type) for ticket_type in TicketType for kind in _VOID_KINDS]
        table = facts.optional_relation(
            self._con, _HEADER_TABLE, (*keys.RACE_KEY, "データ区分", "データ作成年月日", *flag_names, _REFUND_FLAG),
        )
        voids = ", ".join(self._void_select(ticket_type) for ticket_type in TicketType)
        sql = f"""
        SELECT {keys.rid_expr('h')} AS race_id, {voids},
               coalesce({keys.col(_REFUND_FLAG, 'h')} = '{_ON}', FALSE) AS {REFUNDED}
        FROM {table} AS h
        WHERE {keys.col('データ区分', 'h')} IN {keys.sql_list(_PAYOUT_STAGES)} AND {keys.jra_only('h')} AND {days.condition('h')}
        {keys.latest_qualify(keys.RACE_KEY, 'h')}
        ORDER BY race_id
        """
        return self._con.execute(sql, days.params).df()

    def _void_select(self, ticket_type: TicketType) -> str:
        """1つの券種の、不成立か特払なら True の列。"""
        flags = " OR ".join(f"{keys.col(self._flag_name(kind, ticket_type), 'h')} = '{_ON}'" for kind in _VOID_KINDS)
        return f"coalesce({flags}, FALSE) AS {void_column(ticket_type)}"

    def _flag_name(self, kind: str, ticket_type: TicketType) -> str:
        return f"{kind}{_SEPARATOR}{ticket_type.label}"
