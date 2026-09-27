"""1レースの、いま DB にあるいちばん新しい単複枠のオッズの断面（発表時刻）を読む。"""

from __future__ import annotations

import duckdb

from 共通 import facts, keys

_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", "発表月日時分")
#: 使う断面のデータ区分（1 中間・2 前日売最終・3 最終・4 確定・5 確定(月曜)）。9 中止は使わない。
_STAGES: tuple[str, ...] = ("1", "2", "3", "4", "5")


class OddsSnapshotRepository:
    """予想に使ったオッズが、いつの断面かを記録するために読む（``o1``）。

    予想は確定の断面があればそれを、無ければ締め切り前のいちばん新しい断面を使う（``PlaceOddsRepository`` と同じ選び方）。
    フォワードテストでは発走前に予想するので、ここで読む断面は締め切り前のものになるはずである。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> tuple[str, str] | None:
        """（データ区分, 発表月日時分）。断面が無ければ None。"""
        header = facts.optional_relation(self._con, "o1", _HEADER_COLUMNS)
        is_final = f"{keys.q('データ区分')} IN ('4', '5')"
        row = self._con.execute(
            f"""
            SELECT {keys.q('データ区分')}, {keys.q('発表月日時分')} FROM {header}
            WHERE {keys.rid_expr()} = ? AND {keys.q('データ区分')} IN {keys.sql_list(_STAGES)}
            ORDER BY ({is_final}) DESC, {keys.q('発表月日時分')} DESC LIMIT 1
            """,
            [race_id],
        ).fetchone()
        return None if row is None else (row[0], row[1])
