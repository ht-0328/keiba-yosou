"""全走（出走した走）と回顧の不利を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from yosou.review import names
from yosou.review.repository.review_store import ReviewStore

#: 読む事実表の列。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "horse_id", "finish", "time_diff", "last3f_rank", "popularity", "win_payout", "place_payout",
    "surface", "distance_m", "condition",
)


class RunFrameRepository:
    """事実表の出走した走（全期間）を馬ごと・日付順に読み（1 SQL）、回顧の表3「馬の回顧ノート」にある走に ``handicap`` を付ける。

    列は ``COLUMNS`` と ``handicap``（不利があったか）・``placed``（3着以内）・``year``。数の列は小数。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, store: ReviewStore) -> None:
        self._con = con
        self._store = store

    def read(self) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        sql = f"SELECT {', '.join(COLUMNS)} FROM {facts.FACTS_TABLE} WHERE ran ORDER BY horse_id, race_date, race_id"
        frame = self._con.execute(sql).df()
        for column in ("finish", "time_diff", "last3f_rank", "popularity", "win_payout", "place_payout", "distance_m"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
        frame["race_id"] = frame["race_id"].astype(str)
        frame["horse_id"] = frame["horse_id"].astype(str)
        frame["race_date"] = pd.to_datetime(frame["race_date"])
        frame["year"] = frame["race_date"].dt.year
        frame["placed"] = (frame["finish"] <= 3).fillna(False).astype(float)
        frame["handicap"] = self._handicaps(frame)
        return frame.reset_index(drop=True)

    def _handicaps(self, frame: pd.DataFrame) -> pd.Series:
        """回顧の表3に行がある走なら True。回顧のファイルが無ければ全部 False。"""
        if not self._store.path.exists():
            return pd.Series(False, index=frame.index)
        notes = self._store.read(names.HORSES_TABLE)
        keys = set(zip(notes[names.RACE_ID].astype(str), notes[names.HORSE_ID].astype(str)))
        return pd.Series([(race, horse) in keys for race, horse in zip(frame["race_id"], frame["horse_id"])], index=frame.index)
