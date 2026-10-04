"""騎手・調教師の近1年の勝ち切る材料（まとまり Q）を、事実表から読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope

#: 数える期間（開催日の前日までの日数）。
WINDOW_DAYS = 365
#: 件数が少ないときに寄せる先の値と、その重み（疑似の件数）。勝ち切り率は 1着 ÷ 連対 なので 0.5 に、1番人気の勝率は中央の1番人気の勝率に寄せる。
FINISH_PRIOR, FAVORITE_PRIOR, PRIOR_WEIGHT = 0.5, 0.33, 20.0
#: 出す列（特徴量の名前そのまま）。
PEOPLE_FINISH_NAMES: tuple[str, ...] = (
    "勝ち切り_騎手_勝ち切り率_1年", "勝ち切り_騎手_1番人気の勝率_1年", "勝ち切り_調教師_勝ち切り率_1年", "勝ち切り_調教師_1番人気の勝率_1年",
)


class PeopleFinishRepository:
    """対象の出走ごとに、その騎手と調教師の「開催日の前日までの1年間」の勝ち切り率と1番人気のときの勝率を数える（``PEOPLE_FINISH_NAMES``）。

    - 勝ち切り率 = (1着数 + 20 × 0.5) ÷ (1着数 + 2着数 + 20)。連対のうち勝ち切った割合。
    - 1番人気の勝率 = (1番人気で1着 + 20 × 0.33) ÷ (1番人気の出走 + 20)。期待された馬をきちんと勝たせる力。
    件数が少ない人は全体の値（0.5・0.33）に寄せる。事実表の出走した行を人ごと・日ごとに数えてから、日付の範囲の窓で1年ぶんを足す
    （対象の開催日そのものは数えない。対象の日に記録が無くても、その日の時点の値が出るように、対象の日を空の行として足す）。
    研究「回収率100超の施策」で、当日の1着のモデルに足すと確率の誤差が小さくなった（設計書 15 の 15）。
    列は race_id・horse_id と ``PEOPLE_FINISH_NAMES``。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        frame = self._con.execute(self._sql(scope)).df().astype({"race_id": str, "horse_id": str})
        return frame[["race_id", "horse_id", *PEOPLE_FINISH_NAMES]]

    def _sql(self, scope: TargetScope) -> str:
        jockey_rate, jockey_favorite, trainer_rate, trainer_favorite = PEOPLE_FINISH_NAMES
        return f"""
        WITH target AS (
            SELECT race_id, horse_id, CAST(race_date AS DATE) AS day, jockey_code, trainer_code FROM {scope.relation}
        ), runs AS (
            SELECT CAST(race_date AS DATE) AS day, jockey_code, trainer_code, finish, popularity
            FROM {facts.FACTS_TABLE}
            WHERE ran AND CAST(race_date AS DATE) >= (SELECT min(day) FROM target) - {WINDOW_DAYS}
              AND CAST(race_date AS DATE) < (SELECT max(day) FROM target)
        ), {self._yearly('jockey', 'jockey_code')}, {self._yearly('trainer', 'trainer_code')}
        SELECT t.race_id, t.horse_id,
               {self._rate('j')} AS "{jockey_rate}", {self._favorite('j')} AS "{jockey_favorite}",
               {self._rate('tr')} AS "{trainer_rate}", {self._favorite('tr')} AS "{trainer_favorite}"
        FROM target AS t
        LEFT JOIN jockey_year AS j ON j.code = t.jockey_code AND j.day = t.day
        LEFT JOIN trainer_year AS tr ON tr.code = t.trainer_code AND tr.day = t.day
        ORDER BY t.race_id, t.horse_id
        """

    def _yearly(self, name: str, code: str) -> str:
        """人ごと・日ごとの回数（対象の日は空の行として足す）を数え、その日の前日までの1年ぶんを足す CTE（``<name>_days``・``<name>_year``）。"""
        return f"""{name}_days AS (
            SELECT code, day, sum(wins) AS wins, sum(seconds) AS seconds, sum(favorite_runs) AS favorite_runs, sum(favorite_wins) AS favorite_wins
            FROM (
                SELECT {code} AS code, day,
                       CASE WHEN finish = 1 THEN 1 ELSE 0 END AS wins, CASE WHEN finish = 2 THEN 1 ELSE 0 END AS seconds,
                       CASE WHEN popularity = 1 THEN 1 ELSE 0 END AS favorite_runs,
                       CASE WHEN popularity = 1 AND finish = 1 THEN 1 ELSE 0 END AS favorite_wins
                FROM runs WHERE {code} IN (SELECT DISTINCT {code} FROM target WHERE {code} IS NOT NULL)
                UNION ALL
                SELECT DISTINCT {code} AS code, day, 0, 0, 0, 0 FROM target WHERE {code} IS NOT NULL
            )
            GROUP BY code, day
        ), {name}_year AS (
            SELECT code, day, sum(wins) OVER w AS wins, sum(seconds) OVER w AS seconds,
                   sum(favorite_runs) OVER w AS favorite_runs, sum(favorite_wins) OVER w AS favorite_wins
            FROM {name}_days
            WINDOW w AS (PARTITION BY code ORDER BY day RANGE BETWEEN INTERVAL {WINDOW_DAYS} DAY PRECEDING AND INTERVAL 1 DAY PRECEDING)
        )"""

    def _rate(self, alias: str) -> str:
        return (f"(coalesce({alias}.wins, 0) + {PRIOR_WEIGHT} * {FINISH_PRIOR}) / "
                f"(coalesce({alias}.wins, 0) + coalesce({alias}.seconds, 0) + {PRIOR_WEIGHT})")

    def _favorite(self, alias: str) -> str:
        return (f"(coalesce({alias}.favorite_wins, 0) + {PRIOR_WEIGHT} * {FAVORITE_PRIOR}) / "
                f"(coalesce({alias}.favorite_runs, 0) + {PRIOR_WEIGHT})")
