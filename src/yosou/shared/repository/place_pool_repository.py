"""1レースの複勝の票数（売上の見込み）を読む。"""

from __future__ import annotations

import duckdb

from 共通 import keys


class PlacePoolRepository:
    """速報オッズ（``o1``）のいちばん新しい断面から、1レースの複勝票数合計（100円 = 1票）を読む。

    複勝1点の額の上限（その複勝プールの売上の見込みの 0.5%。設計書「買うレースと買い目を決める」08 の 1）に使う。
    締め切り前の断面は確定より少ないので、上限は控えめになる。無ければ None。元DB は読むだけ。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> int | None:
        cond, params = keys.rid_condition(race_id)
        row = self._con.execute(
            f"""SELECT TRY_CAST("複勝票数合計" AS BIGINT) FROM o1 WHERE {cond}
                AND {keys.q('データ区分')} NOT IN ('0', '9') ORDER BY "発表月日時分" DESC LIMIT 1""", params,
        ).fetchone()
        return int(row[0]) if row and row[0] is not None and int(row[0]) > 0 else None
