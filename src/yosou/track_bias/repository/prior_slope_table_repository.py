"""レースごとの傾きと、過去の傾きの表を pickle のファイルに書く・読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.repository import StampFile

from ..prior_slope_table import PriorSlopeTable

#: レースごとの傾きの表と、過去の傾きの表のファイル。元DB の印は隣の ``stamp.json``（``StampFile``）。
SLOPES_FILE, TABLE_FILE = "傾き.pkl", "過去の傾き.pkl"


class PriorSlopeTableRepository:
    """レースごとの傾き（``RaceSlopes`` の表）と過去の傾きの表（``PriorSlopeTable``）を ``folder`` に pickle で書く・読む。
    元DB の印は ``stamp.json`` に一緒に書く。今の元DB から作ったものかの判断は ``PriorSlopeTableStore`` がする。"""

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)
        self._stamp = StampFile(self._folder, (SLOPES_FILE, TABLE_FILE))

    def saved_stamp(self) -> dict[str, object] | None:
        """とっておいた表を作った元DB の印。表か印が無ければ None。"""
        return self._stamp.read()

    def read(self) -> tuple[pd.DataFrame, PriorSlopeTable]:
        """（レースごとの傾きの表, 過去の傾きの表）。"""
        saved = pd.read_pickle(self._folder / TABLE_FILE)
        return pd.read_pickle(self._folder / SLOPES_FILE), PriorSlopeTable(saved["cells"], saved["courses"], saved["as_of"])

    def write(self, slopes: pd.DataFrame, table: PriorSlopeTable, stamp: dict[str, object]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        slopes.to_pickle(self._folder / SLOPES_FILE)
        pd.to_pickle({"cells": table.cells, "courses": table.courses, "as_of": table.as_of}, self._folder / TABLE_FILE)
        self._stamp.write(stamp, table.as_of)
