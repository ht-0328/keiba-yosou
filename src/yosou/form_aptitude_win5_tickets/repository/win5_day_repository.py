"""1つの開催日の WIN5（対象レース5つ・キャリーオーバー金額初期）を読む。"""

from __future__ import annotations

from datetime import date

import duckdb

from 共通 import facts, keys

from .win5_day import Win5Day

#: 重勝式の親の表と、対象レースの子表（列はこの SQL が読むものだけ）。
_DAY_TABLE = "wf"
_RACE_TABLE = "wf__重勝式対象レース情報"
_DAY_COLUMNS = ("開催年", "開催月日", "データ区分", "キャリーオーバー金額初期")
_RACE_COLUMNS = ("開催年", "開催月日", "_連番", *keys.RACE_KEY[2:])
#: 中止のデータ区分。
_CANCELLED_STAGE = "9"
#: WIN5 の対象レースの数。
LEG_COUNT = 5


class Win5DayRepository:
    """元DB の ``wf`` と子表 ``wf__重勝式対象レース情報`` から、1つの開催日の WIN5 を読んで ``Win5Day`` にする（SQL 1本）。

    当日の分は jvdata-store の ``jvstore realtime`` が速報の WIN5（``0B51``）で同じ表に入れる。終わった回は成績の版（データ区分 7）。
    同じ開催日の行は1つ（いちばん新しい版）しか入らない。表の無い DB では空の関係で代わりにし、「無い」と案内する。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_date: date) -> Win5Day:
        """その日の WIN5。無い・中止・対象レースが5つそろっていなければ ``LookupError``（取り込みの案内つき）。"""
        rows = self._con.execute(self._sql(), [race_date.strftime("%Y"), race_date.strftime("%m%d")]).fetchall()
        if not rows:
            raise LookupError(
                f"{race_date.isoformat()} の WIN5 が元DB にありません。jvdata-store で "
                f"`jvstore realtime --date {race_date.isoformat()}` を実行して、速報の WIN5 を取り込んでください"
            )
        stage, carry = rows[0][0], rows[0][1]
        if stage == _CANCELLED_STAGE:
            raise LookupError(f"{race_date.isoformat()} の WIN5 は中止です")
        race_ids = tuple(rid for _, _, rid in rows)
        if len(race_ids) != LEG_COUNT:
            raise LookupError(f"{race_date.isoformat()} の WIN5 の対象レースが {len(race_ids)} つしかありません（5つ要ります）")
        return Win5Day(race_date, race_ids, int(carry or 0))

    def _sql(self) -> str:
        day_table = facts.optional_relation(self._con, _DAY_TABLE, _DAY_COLUMNS)
        race_table = facts.optional_relation(self._con, _RACE_TABLE, _RACE_COLUMNS)
        race_id = " || ".join(keys.col(name, "t") for name in keys.RACE_KEY)
        return f"""
        SELECT w.{keys.q('データ区分')},
               COALESCE(TRY_CAST(w.{keys.q('キャリーオーバー金額初期')} AS BIGINT), 0),
               {race_id}
        FROM {day_table} AS w
        JOIN {race_table} AS t USING ({keys.q('開催年')}, {keys.q('開催月日')})
        WHERE w.{keys.q('開催年')} = ? AND w.{keys.q('開催月日')} = ?
        ORDER BY TRY_CAST(t.{keys.q('_連番')} AS INTEGER)
        """
