"""学習データの全部の行を学ぶ。"""

from __future__ import annotations

import duckdb

from .training_data import TrainingData


class AllRows:
    """``TrainingRows`` の決まりを守る。学習データをそのまま返す（行を絞らない予想の既定）。"""

    def keep(self, con: duckdb.DuckDBPyConnection, data: TrainingData) -> TrainingData:
        return data
