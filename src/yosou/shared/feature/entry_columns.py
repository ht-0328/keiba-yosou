"""出走の記録から列を選び、名前を付け直す。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


class EntryColumns:
    """出走の記録（``EntryRecords.entries``）から列を選び、名前を付け直す。"""

    def __init__(self, source_columns: Mapping[str, str]) -> None:
        """``source_columns`` は「付け直す名前 → 出走の記録の列名」。"""
        self._source_columns = dict(source_columns)

    def select(self, entries: pd.DataFrame) -> pd.DataFrame:
        """選んだ列だけの表。行の並びと index は ``entries`` と同じ。"""
        columns = {name: entries[source] for name, source in self._source_columns.items()}
        return pd.DataFrame(columns, index=entries.index)
