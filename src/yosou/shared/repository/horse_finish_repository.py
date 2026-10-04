"""馬の近10走の勝ち切る材料（まとまり Q）を、事実表から読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope

#: 数える過去走の数。
RUNS = 10
#: 惜敗とみなす着差（秒。勝ち馬とのタイム差がこれ以下の負け）。
NEAR_MISS_SECONDS = 0.2
#: 「人気で負けた」とみなす人気の上限（1〜2番人気で2着以下）。
FAVORITE_UP_TO = 2
#: 出す列（特徴量の名前そのまま）。
HORSE_FINISH_NAMES: tuple[str, ...] = (
    "勝ち切り_1着数_近10走", "勝ち切り_2着数_近10走", "勝ち切り_勝ち切り率_近10走", "勝ち切り_惜敗数_近10走",
    "勝ち切り_勝ち着差の平均_近10走", "勝ち切り_人気で負けた数_近10走",
)


class HorseFinishRepository:
    """対象の出走ごとに、その馬の「開催日より前の近10走」から勝ち切る材料の6列を数える（``HORSE_FINISH_NAMES``）。

    - 1着数・2着数: 近10走の1着と2着の回数。
    - 勝ち切り率: 1着数 ÷（1着数 + 2着数）。連対が無ければ欠損値。
    - 惜敗数: 2着以下で、勝ち馬とのタイム差が 0.2秒以下だった回数。
    - 勝ち着差の平均: 勝ったときの2着馬との差（秒）の平均。勝ちが無ければ欠損値。
    - 人気で負けた数: 1〜2番人気で2着以下だった回数。
    過去走は事実表の出走した行（確定成績）。対象の出走そのものは数えない。過去走が無い馬は、回数は 0、率と平均は欠損値。
    研究「回収率100超の施策」で、当日の1着のモデルに足すと確率の誤差が小さくなった（設計書 15 の 15）。
    列は race_id・horse_id と ``HORSE_FINISH_NAMES``。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        wins, seconds, rate, near, margin, lost = HORSE_FINISH_NAMES
        sql = f"""
        WITH target AS (
            SELECT race_id, horse_id, CAST(race_date AS DATE) AS day FROM {scope.relation} WHERE horse_id IS NOT NULL
        ), runs AS (
            SELECT race_id, horse_id, CAST(race_date AS DATE) AS day, finish, popularity, time_diff
            FROM {facts.FACTS_TABLE}
            WHERE ran AND horse_id IN (SELECT DISTINCT horse_id FROM target)
        ), recent AS (
            SELECT t.race_id, t.horse_id, r.finish, r.popularity, r.time_diff,
                   row_number() OVER (PARTITION BY t.race_id, t.horse_id ORDER BY r.day DESC, r.race_id DESC) AS n
            FROM target AS t
            JOIN runs AS r ON r.horse_id = t.horse_id AND (r.day < t.day OR (r.day = t.day AND r.race_id < t.race_id))
        ), counted AS (
            SELECT race_id, horse_id,
                   sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) AS wins,
                   sum(CASE WHEN finish = 2 THEN 1 ELSE 0 END) AS seconds,
                   sum(CASE WHEN finish >= 2 AND time_diff <= {NEAR_MISS_SECONDS} THEN 1 ELSE 0 END) AS near_misses,
                   sum(CASE WHEN finish >= 2 AND popularity <= {FAVORITE_UP_TO} THEN 1 ELSE 0 END) AS favorite_losses,
                   avg(CASE WHEN finish = 1 THEN -time_diff END) AS win_margin
            FROM recent WHERE n <= {RUNS}
            GROUP BY race_id, horse_id
        )
        SELECT t.race_id, t.horse_id,
               coalesce(c.wins, 0) AS "{wins}", coalesce(c.seconds, 0) AS "{seconds}",
               CASE WHEN coalesce(c.wins, 0) + coalesce(c.seconds, 0) > 0 THEN c.wins * 1.0 / (c.wins + c.seconds) END AS "{rate}",
               coalesce(c.near_misses, 0) AS "{near}", c.win_margin AS "{margin}", coalesce(c.favorite_losses, 0) AS "{lost}"
        FROM target AS t
        LEFT JOIN counted AS c ON c.race_id = t.race_id AND c.horse_id = t.horse_id
        ORDER BY t.race_id, t.horse_id
        """
        frame = self._con.execute(sql).df().astype({"race_id": str, "horse_id": str})
        return frame[["race_id", "horse_id", *HORSE_FINISH_NAMES]]
