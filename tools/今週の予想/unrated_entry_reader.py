"""これから走る1レースの出走馬から、評価できない馬を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from 今週の予想.unrated_horse import UnratedHorse

#: 出走馬に事実表と同じ列を付けた一時表の名前（予想の部品が作る一時表と分ける）。
_TABLE = "unrated_entry_facts"


class UnratedEntryReader:
    """1レース（確定前でもよい）の出走馬の所属と、今回より前の中央の出走数を、事実表と同じ SQL（``facts.build_entry_facts``）で読み、
    評価できない馬か（``UnratedHorse``）を馬ID ごとに返す。道具「印の成績」が終わったレースの事実表から読む値と同じ定義になる。"""

    def read(self, con: duckdb.DuckDBPyConnection, race_id: str) -> pd.Series:
        """馬ID（文字列）を index にした真偽の列。"""
        table = facts.build_entry_facts(con, facts.EntryScope(race_id), name=_TABLE)
        rows = con.execute(f"SELECT horse_id, affiliation, runs_before FROM {table}").df()
        flags = UnratedHorse().of(rows["affiliation"], rows["runs_before"])
        return pd.Series(flags.to_numpy(), index=rows["horse_id"].astype(str))
