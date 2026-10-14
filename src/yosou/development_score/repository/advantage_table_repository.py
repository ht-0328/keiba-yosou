"""表 G を pickle のファイルに書く・読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.repository import StampFile

from ..advantage_table import AdvantageTable

#: 表 G のファイル。元DB の印は隣の ``stamp.json``（``StampFile``）。
TABLE_FILE = "表G.pkl"


class AdvantageTableRepository:
    """表 G（``AdvantageTable``）を ``folder`` に pickle で書く・読む。元DB の印は ``stamp.json`` に一緒に書く。
    今の元DB から作ったものかの判断は ``AdvantageTableStore`` がする。"""

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)
        self._stamp = StampFile(self._folder, (TABLE_FILE,))

    def saved_stamp(self) -> dict[str, object] | None:
        """とっておいた表 G を作った元DB の印。表か印が無ければ None。"""
        return self._stamp.read()

    def read(self) -> AdvantageTable:
        saved = pd.read_pickle(self._folder / TABLE_FILE)
        return AdvantageTable(saved["frame"], saved["pool"], saved["as_of"])

    def write(self, table: AdvantageTable, stamp: dict[str, object]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"frame": table.frame, "pool": table.pool, "as_of": table.as_of}, self._folder / TABLE_FILE)
        self._stamp.write(stamp, table.as_of)
