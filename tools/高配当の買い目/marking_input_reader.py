"""印を付けるのに要るものを、元DB からまとめて読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 印の成績.odds_snapshot_repository import OddsSnapshotRepository
from 印の成績.pool_win_reader import PoolWinReader
from 印の成績.race_results import RaceResults

from 高配当の買い目.marking_inputs import MarkingInputs


class MarkingInputReader:
    """元DB を開いている間に行う「読む段」。道具「印の成績」の読む部品（``RaceResults``・``PoolWinReader``・``OddsSnapshotRepository``）を順に呼ぶ。

    計算（印付け）はここではしない。元DB のロックを長く持たないように、呼ぶ側は読み終えたら元DB を閉じてから ``HorseMarker`` に渡す。
    ``result_race_ids`` は結果を読むレース（印を付けるレースと、危険な人気馬の線・単勝の期待値を出すレース）、
    ``marked_race_ids`` は印を付けるレース（3連単のオッズと時系列オッズは重いので、このレースだけ読む）。
    """

    def read(self, con: duckdb.DuckDBPyConnection, result_race_ids: pd.Series, marked_race_ids: pd.Series) -> MarkingInputs:
        results = RaceResults().read(con, result_race_ids)
        pools = PoolWinReader().read(con, marked_race_ids)
        movements = OddsSnapshotRepository().read(con, marked_race_ids)
        return MarkingInputs(results, pools, movements)
