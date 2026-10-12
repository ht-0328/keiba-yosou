"""学習データのうち、学ぶ行の選び方の決まり。"""

from __future__ import annotations

from typing import Protocol

import duckdb

from .training_data import TrainingData


class TrainingRows(Protocol):
    """作った学習データから、学ぶ行だけを残す決まり（インターフェース）。

    元DB を開いている間に呼ぶので、行を選ぶのに要るもの（レースごとの払戻など）を ``con`` から読んでよい。
    守るクラスは、全部の行を残す ``AllRows``（今の本番の予想）と、荒れたレースだけを残す
    ``yosou.upset_premise`` の ``WildRaceRows``（荒れる前提で着順を予想）。
    """

    def keep(self, con: duckdb.DuckDBPyConnection, data: TrainingData) -> TrainingData:
        ...
