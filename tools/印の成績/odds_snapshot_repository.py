"""前日夜と当日朝の単勝オッズ（時系列オッズの断面）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from 印の成績.filter_columns import ODDS_EVENING, ODDS_MORNING

#: オッズ1（単複枠）の親と、馬番ごとの単勝オッズの子。
_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__単勝オッズ"
_ANNOUNCED = "発表月日時分"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", _ANNOUNCED)
_ODDS_COLUMNS = (*keys.RACE_KEY, _ANNOUNCED, "馬番", "オッズ")
#: 中間の断面のデータ区分（発表月日時分が入るのは中間だけ）。
_INTERIM_STAGE = "1"
#: 当日朝の断面の締め（時分）。これ以前のいちばん新しい断面を「当日朝」にする。
MORNING_CUTOFF = "0930"
#: 単勝オッズの「無投票」（オッズは 10倍の4桁の文字列）。
_NO_ODDS = "0000"
_ODDS_SCALE = 10.0
#: 読むレースIDを入れる一時表。
_WANTED = "mark_stats_snapshot_races"


class OddsSnapshotRepository:
    """``race_ids`` のレースについて、前日の最後の断面と、当日 9時30分までの最後の断面の単勝オッズを馬ごとに読む
    （研究「回収率100超の施策」の施策5。前日夜 → 当日朝のオッズの動きを見る）。

    断面は時系列オッズ（``o1`` のデータ区分 1）の ``発表月日時分``（MMDDhhmm）で見分け、開催月日より前の日付を前日、
    開催月日と同じ日付の 9時30分以前を当日朝とする。両方の断面があるレースの馬だけ返す（時系列オッズは JV-Data の提供が1年ぶんなので、
    古いレースは行が無い）。列は race_id・horse_no・``odds_evening``・``odds_morning``（倍。無投票は欠損値）。
    """

    def read(self, con: duckdb.DuckDBPyConnection, race_ids: pd.Series) -> pd.DataFrame:
        header = facts.optional_relation(con, _HEADER_TABLE, _HEADER_COLUMNS)
        child = facts.optional_relation(con, _ODDS_TABLE, _ODDS_COLUMNS)
        con.register("mark_stats_snapshot_race_ids", pd.DataFrame({"race_id": race_ids.astype(str).drop_duplicates()}))
        con.execute(f"CREATE OR REPLACE TEMP TABLE {_WANTED} AS SELECT * FROM mark_stats_snapshot_race_ids")
        announced = keys.q(_ANNOUNCED)
        odds_value = f"TRY_CAST(NULLIF(o.{keys.q('オッズ')}, '{_NO_ODDS}') AS INTEGER) / {_ODDS_SCALE}"
        sql = f"""
        WITH snapshots AS (
            SELECT {keys.rid_expr('h')} AS race_id, h.{keys.q('開催月日')} AS race_mmdd, h.{announced} AS announced
            FROM {header} AS h
            WHERE {keys.rid_expr('h')} IN (SELECT race_id FROM {_WANTED})
              AND h.{keys.q('データ区分')} = '{_INTERIM_STAGE}' AND length(h.{announced}) = 8
        ), evening AS (
            SELECT race_id, max(announced) AS announced FROM snapshots WHERE substr(announced, 1, 4) < race_mmdd GROUP BY race_id
        ), morning AS (
            SELECT race_id, max(announced) AS announced FROM snapshots
            WHERE substr(announced, 1, 4) = race_mmdd AND substr(announced, 5, 4) <= '{MORNING_CUTOFF}' GROUP BY race_id
        ), odds AS (
            SELECT {keys.rid_expr('o')} AS race_id, o.{announced} AS announced,
                   TRY_CAST(o.{keys.q('馬番')} AS INTEGER) AS horse_no, {odds_value} AS odds
            FROM {child} AS o
            WHERE {keys.rid_expr('o')} IN (SELECT race_id FROM {_WANTED})
        )
        SELECT evening.race_id, oe.horse_no, oe.odds AS {ODDS_EVENING}, om.odds AS {ODDS_MORNING}
        FROM evening
        JOIN morning USING (race_id)
        JOIN odds AS oe ON oe.race_id = evening.race_id AND oe.announced = evening.announced
        JOIN odds AS om ON om.race_id = morning.race_id AND om.announced = morning.announced AND om.horse_no = oe.horse_no
        WHERE oe.horse_no IS NOT NULL
        ORDER BY evening.race_id, oe.horse_no
        """
        return con.execute(sql).df().astype({"race_id": str, "horse_no": int})
