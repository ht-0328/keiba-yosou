"""過去の傾きの表を、年ごとにファイルにとっておく。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.repository import DbStamp
from yosou.track_bias import BiasRunRepository, PriorSlopeTable, PriorSlopeTableBuilder, RaceSlopes


class PriorSlopeYearStore:
    """「``before``（その年の1月1日）より前のレースだけで作った過去の傾きの表」（``PriorSlopeTableBuilder``）を、
    ``folder/過去の傾き-<before>.pkl`` にとっておく。

    中身は、同じ元DB（ファイルのパス）なら年が変わるまで変わらない（過去のレースは増えない）ので、ファイルがあれば読むだけ。
    無ければ元DB の全出走（``BiasRunRepository``）からレースごとの傾き（``RaceSlopes``）を出して作る（地方の元DB で1分ほど）。
    中央の ``PriorSlopeTableStore`` は元DB の更新時刻で作り直すが、地方の元DB は速報の取り込みで日に何度も更新されるので、
    発走前に毎回1分かけないよう、年の区切りでとっておく。学習データの U（``LocalBiasHistory``）と同じ決めごとになる。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def path(self, before: date) -> Path:
        return self._folder / f"過去の傾き-{before.isoformat()}.pkl"

    def load(self, con: duckdb.DuckDBPyConnection, before: date) -> PriorSlopeTable:
        """とっておいた表（同じ元DB のもの）か、作って書いた表。"""
        path = self.path(before)
        db_path = str(DbStamp().db_path_of(con).resolve())
        if path.exists():
            saved = pd.read_pickle(path)
            if saved.get("db") == db_path and saved.get("before") == before.isoformat():
                return PriorSlopeTable(saved["cells"], saved["courses"], saved["as_of"])
        table = PriorSlopeTableBuilder().build(RaceSlopes().of(BiasRunRepository(con).read()), before=before)
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"cells": table.cells, "courses": table.courses, "as_of": table.as_of, "db": db_path, "before": before.isoformat()}, path)
        return table
