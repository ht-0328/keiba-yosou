"""時系列オッズ（0B41 を取り込んだ o1 の表）から、1レースの馬ごとの「今・前の断面・最初」の単勝オッズと、今と約10分前の複勝オッズを読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

#: 動きを見る前の断面は、今の断面の何分前か（列の名前 → 分）。その時刻かそれより前で、いちばん新しい断面を取る。
EARLIER_A = 10
EARLIER_B = 20
EARLIER: dict[str, int] = {"odds_back2": 2, "odds_back5": 5, "odds_a": EARLIER_A, "odds_b": EARLIER_B, "odds_back35": 35}
#: 発売中の断面のデータ区分（1 = 中間）。締め切り後の断面（確定）は、買い目を決める材料にしない。
_ON_SALE = "1"

#: 発表月日時分（MMDDhhmm）→ その月の中での分。同じ開催日の中の差だけに使う。
_MINUTE = "(CAST(substr(発表月日時分, 3, 2) AS INTEGER) * 24 + CAST(substr(発表月日時分, 5, 2) AS INTEGER)) * 60 + CAST(substr(発表月日時分, 7, 2) AS INTEGER)"

_EARLIER_COLUMNS = ",\n           ".join(f"arg_max(w.odds, w.minute) FILTER (WHERE w.minute <= n.minute - {minutes}) AS {name}" for name, minutes in EARLIER.items())

_SQL = f"""
WITH win AS (
    SELECT DISTINCT 発表月日時分 AS announced, {_MINUTE} AS minute, CAST(馬番 AS INTEGER) AS horse_no, TRY_CAST(オッズ AS DOUBLE) / 10.0 AS odds
    FROM {keys.q('o1__単勝オッズ')} d
    WHERE {keys.rid_expr('d')} = ? AND TRY_CAST(オッズ AS DOUBLE) > 0
      AND 発表月日時分 IN (SELECT 発表月日時分 FROM o1 h WHERE {keys.rid_expr('h')} = ? AND h.データ区分 = '{_ON_SALE}')
), now AS (
    SELECT max(minute) AS minute FROM win
), place AS (
    SELECT DISTINCT {_MINUTE} AS minute, CAST(馬番 AS INTEGER) AS horse_no,
           TRY_CAST(最低オッズ AS DOUBLE) / 10.0 AS place_low, TRY_CAST(最高オッズ AS DOUBLE) / 10.0 AS place_high
    FROM {keys.q('o1__複勝オッズ')} d
    WHERE {keys.rid_expr('d')} = ? AND TRY_CAST(最低オッズ AS DOUBLE) > 0
), win_wide AS (
    SELECT w.horse_no,
           arg_max(w.odds, w.minute) AS odds_now,
           {_EARLIER_COLUMNS},
           arg_min(w.odds, w.minute) AS odds_first,
           max(w.announced) AS announced
    FROM win w CROSS JOIN now n
    GROUP BY w.horse_no
), place_wide AS (
    SELECT p.horse_no,
           max(p.place_low) FILTER (WHERE p.minute = n.minute) AS place_low,
           max(p.place_high) FILTER (WHERE p.minute = n.minute) AS place_high,
           arg_max(p.place_low, p.minute) FILTER (WHERE p.minute <= n.minute - {EARLIER_A}) AS place_low_a
    FROM place p CROSS JOIN now n
    GROUP BY p.horse_no
)
SELECT w.horse_no, w.odds_now, w.odds_a, w.odds_b, w.odds_first, w.odds_back2, w.odds_back5, w.odds_back35,
       p.place_low, p.place_high, p.place_low_a, w.announced
FROM win_wide w
LEFT JOIN place_wide p ON p.horse_no = w.horse_no
ORDER BY w.horse_no
"""


@dataclass(frozen=True)
class OddsSnapshotRepository:
    """列は ``horse_no``・``odds_now``・``odds_a``（約10分前）・``odds_b``（約20分前）・``odds_first``・``odds_back2``・``odds_back5``・``odds_back35``
    （約2分前・約5分前・約35分前）・``place_low``・``place_high``・``place_low_a``（約10分前の複勝の下）・``announced``（今の断面の発表月日時分）。
    今の断面にオッズの無い馬（取消）は、前の断面のオッズが ``odds_now`` に入るので、呼ぶ側は ``announced`` がいちばん新しい行だけを使う。
    前の断面が無ければ、その列は欠損。断面が1つも無ければ空の表。"""

    con: duckdb.DuckDBPyConnection

    def load(self, rid: str) -> pd.DataFrame:
        frame = self.con.execute(_SQL, [rid, rid, rid]).df()
        return frame[frame["announced"] == frame["announced"].max()].reset_index(drop=True) if len(frame) else frame
