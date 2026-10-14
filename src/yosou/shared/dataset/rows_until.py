"""学習データから、ある日より後の行を落とす。"""

from __future__ import annotations

from datetime import date

import duckdb

from .training_data import TrainingData


class RowsUntil:
    """``TrainingRows`` の決まりを守る。開催日が ``end``（その日を含まない）より前の行だけを残す。

    7つの区切りでの確かめ（特別登録の予想の設計書 16 の 4）で、全期間で1回作った学習データを、区切りの終わり
    （テスト期間の終わり）で切るのに使う。``end`` が None なら全部の行を残す。元DB は使わない。
    """

    def __init__(self, end: date | None) -> None:
        self._end = end

    def keep(self, con: duckdb.DuckDBPyConnection | None, data: TrainingData) -> TrainingData:
        if self._end is None:
            return data
        return data.between(None, self._end)
