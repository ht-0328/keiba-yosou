"""速報の馬場状態を読む。"""

from __future__ import annotations

import duckdb

from 共通 import codes, facts, keys

#: 開催日と競馬場を決める鍵（レースの鍵6列から、レース番号を除いた5列）。速報の馬場状態はこの単位で発表される。
_MEETING_KEY = keys.RACE_KEY[:-1]
#: 変更識別のうち、馬場状態が入っているもの（1 初期状態・3 馬場状態変更）。2 は天候変更で、馬場状態は入っていない。
_GOING_CHANGES: tuple[str, ...] = ("1", "3")
#: ダートのコースのトラックコードの範囲。この範囲ならダートの、それ以外は芝の馬場状態を使う。
_DIRT_TRACK_FIRST, _DIRT_TRACK_LAST = "23", "29"
_TURF_GOING, _DIRT_GOING = "馬場状態・芝", "馬場状態・ダート"
_NEEDED_COLUMNS = (*_MEETING_KEY, "発表月日時分", "変更識別", _TURF_GOING, _DIRT_GOING)


class AnnouncedGoingRepository:
    """速報の天候馬場状態（we）から、そのレースの競馬場・開催日で最後に発表された馬場状態を読む。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> str | None:
        """馬場状態コード（1 良〜4 不良）。速報が無ければ None。we の表が無い DB では空の関係で代わりにする。"""
        we_table = facts.optional_relation(self._con, "we", _NEEDED_COLUMNS)
        race_condition, race_values = keys.rid_condition(race_id)
        meeting_condition = " AND ".join(f"w.{keys.q(name)} = ?" for name in _MEETING_KEY)
        meeting_values = race_values[:len(_MEETING_KEY)]
        sql = f"""
        WITH race AS (
            SELECT {keys.q('トラックコード')} AS track_code FROM ra
            WHERE {race_condition}
            ORDER BY {keys.q('データ区分')} DESC LIMIT 1
        ), announced AS (
            SELECT w.{keys.q('発表月日時分')} AS announced_at,
                   CASE WHEN race.track_code BETWEEN '{_DIRT_TRACK_FIRST}' AND '{_DIRT_TRACK_LAST}'
                        THEN w.{keys.q(_DIRT_GOING)} ELSE w.{keys.q(_TURF_GOING)} END AS going_code
            FROM {we_table} AS w, race
            WHERE {meeting_condition}
              AND w.{keys.q('変更識別')} IN {keys.sql_list(_GOING_CHANGES)}
        )
        SELECT going_code FROM announced
        WHERE going_code IN {keys.sql_list(codes.TRACK_CONDITION)}
        ORDER BY announced_at DESC LIMIT 1
        """
        row = self._con.execute(sql, [*race_values, *meeting_values]).fetchone()
        return row[0] if row else None
