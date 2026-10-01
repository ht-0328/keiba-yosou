"""締め切り前の単勝オッズで1番人気だった馬を、元DB から読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

#: レース（発走時刻）と、オッズ1（単複枠）の親と、馬番ごとの単勝オッズの子。
_RACE_TABLE = "ra"
_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__単勝オッズ"
_RACE_COLUMNS = (*keys.RACE_KEY, "データ区分", "データ作成年月日", "発走時刻")
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", "発表月日時分")
_ODDS_COLUMNS = (*keys.RACE_KEY, "発表月日時分", "馬番", "オッズ")
#: 使う断面のデータ区分（1 中間・2 前日売最終）。3 最終は締め切りの時点の断面で、買う時点には見えない。
_PRE_DEADLINE_STAGES: tuple[str, ...] = ("1", "2")
#: レースの行のうち、使わないデータ区分（0 削除・9 中止）。
_UNUSED_RACE_STAGES: tuple[str, ...] = ("0", "9")
#: 単勝オッズの「無投票」。オッズは 10倍した4桁の文字列で入っている（取消は ---- か ****）。
_NO_ODDS = "0000"
_ODDS_SCALE = 10.0


class PreDeadlineFavoriteRepository:
    """レースごとに、発走の ``minutes`` 分前までに発表された締め切り前の単勝オッズの断面のうち、いちばん新しいものを選び、
    その断面で単勝オッズがいちばん低かった馬（締め切り前の1番人気）を読む（設計書 16 の 7）。

    断面は、jvdata-store が時系列オッズ（``0B41``）か速報オッズ（``0B30``）で元DB に入れたもの。今の元DB では
    過去1年ほどのレースにしか無く、断面の無いレースは行が出ない。オッズの同じ馬が並んだら、どれも1番人気にする
    （確定の単勝人気で同じ1番人気が2頭いるときと同じ扱い）。

    共通の ``AnnouncedOddsRepository`` は使わない。あれは予測する1レースだけを読み、締め切りの時点の断面
    （データ区分 3 最終）も含めて、発走の何分前かを区切らずにいちばん新しい断面を選ぶためである。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, minutes: int) -> None:
        self._con = con
        self._minutes = minutes

    def read(self) -> pd.DataFrame:
        """列は ``race_id``・``horse_no``・``odds``（倍）。1行 = 締め切り前の1番人気1頭。"""
        races = facts.optional_relation(self._con, _RACE_TABLE, _RACE_COLUMNS)
        headers = facts.optional_relation(self._con, _HEADER_TABLE, _HEADER_COLUMNS)
        odds_table = facts.optional_relation(self._con, _ODDS_TABLE, _ODDS_COLUMNS)
        stage, announced, start = keys.q("データ区分"), keys.q("発表月日時分"), keys.q("発走時刻")
        year, month_day = keys.q("開催年"), keys.q("開催月日")
        odds_value = f"TRY_CAST(NULLIF(o.{keys.q('オッズ')}, '{_NO_ODDS}') AS INTEGER)"
        sql = f"""
        WITH starts AS (
            SELECT {keys.rid_expr()} AS race_id,
                   strftime(make_timestamp(CAST({year} AS BIGINT), CAST(substr({month_day}, 1, 2) AS BIGINT),
                                           CAST(substr({month_day}, 3, 2) AS BIGINT), CAST(substr({start}, 1, 2) AS BIGINT),
                                           CAST(substr({start}, 3, 2) AS BIGINT), 0.0)
                            - to_minutes(CAST(? AS BIGINT)), '%m%d%H%M') AS cutoff
            FROM {races}
            WHERE {stage} NOT IN {keys.sql_list(_UNUSED_RACE_STAGES)} AND {start} NOT IN ('', '0000')
            QUALIFY row_number() OVER (PARTITION BY {keys.key_list()}
                                       ORDER BY {stage} DESC, {keys.q('データ作成年月日')} DESC) = 1
        ),
        snapshots AS (
            SELECT s.race_id, h.{announced} AS announced
            FROM {headers} AS h JOIN starts AS s ON s.race_id = {keys.rid_expr('h')}
            WHERE h.{stage} IN {keys.sql_list(_PRE_DEADLINE_STAGES)} AND h.{announced} <= s.cutoff
            QUALIFY row_number() OVER (PARTITION BY s.race_id ORDER BY h.{announced} DESC) = 1
        )
        SELECT n.race_id, TRY_CAST(o.{keys.q('馬番')} AS INTEGER) AS horse_no, {odds_value} / {_ODDS_SCALE} AS odds
        FROM {odds_table} AS o JOIN snapshots AS n
          ON {keys.rid_expr('o')} = n.race_id AND o.{announced} = n.announced
        WHERE {odds_value} IS NOT NULL AND TRY_CAST(o.{keys.q('馬番')} AS INTEGER) IS NOT NULL
        QUALIFY rank() OVER (PARTITION BY n.race_id ORDER BY odds) = 1
        ORDER BY n.race_id, horse_no
        """
        return self._con.execute(sql, [self._minutes]).df()
