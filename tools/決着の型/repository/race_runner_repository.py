"""事実表から、レースと出走（人気・オッズ・着順・馬番・単複の払戻）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts
from 共通.filters import Filters

#: 読む列。レース単位の列（開催日・競馬場・レース番号・頭数）と、出走ごとの列（馬番・人気・オッズ・着順・払戻・馬齢）。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "year", "venue", "race_no", "field_size",
    "horse_no", "popularity", "win_odds", "finish", "win_payout", "place_payout", "age",
)


class RaceRunnerRepository:
    """条件に合うレースの、出走した馬の行（1行 = 1頭）を事実表から読む。

    絞り込みはレース単位の項目（競馬場・芝ダ・コース・距離・馬場・クラス・頭数・期間・月）で使う。
    出走馬の条件（人気・枠 …）を渡すと、その馬だけが残ってレースの形が壊れるので渡さない。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, filters: Filters = Filters()) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        where, params = filters.where()
        sql = f"""
        SELECT {", ".join(COLUMNS)}
        FROM {facts.FACTS_TABLE}
        WHERE ran AND {where}
        ORDER BY race_id, horse_no
        """
        return self._con.execute(sql, params).df()
