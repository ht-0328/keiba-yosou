"""出走別着度数（ck）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from .career_count_sql import CareerCountSql
from .target_scope import TargetScope

#: 削除されたレコードのデータ区分。
_DELETED = "0"


class CareerCountRepository:
    """対象の出走それぞれの、出走別着度数（その出走の出走馬名表の時点の、通算の着回数）を読む。

    通算と、そのレースの条件（競馬場・距離帯・馬場状態）に合う欄の、出走数と3着以内の数を返す。
    2023年より前の出走も含む数なので、DB にある過去走から数えるより正しい（設計書 09 の「表の見方」）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con
        self._counts = CareerCountSql(ck="c", entry="t")

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """1行 = 1頭の出走。列は ``race_id``・``horse_id`` と、``ck_`` で始まる9つの数。

        ck に行が無い出走は返さない。ck の表が無い DB では、同じ列を持つ空の関係で代わりにする。
        jvdata-store は ck をレース・馬ごとに1行（新しい版）だけ持つので、最新の行を選び直さない。
        """
        needed_columns = (*keys.RACE_KEY, keys.HORSE_KEY, "データ区分", *self._counts.source_columns())
        ck_table = facts.optional_relation(self._con, "ck", needed_columns)
        sql = f"""
        SELECT t.race_id, t.horse_id,
               {self._counts.select_list()}
        FROM {scope.relation} AS t
        JOIN {ck_table} AS c
          ON {keys.rid_expr("c")} = t.race_id AND c.{keys.q(keys.HORSE_KEY)} = t.horse_id
        WHERE c.{keys.q('データ区分')} <> '{_DELETED}'
        """
        return self._con.execute(sql).df()
