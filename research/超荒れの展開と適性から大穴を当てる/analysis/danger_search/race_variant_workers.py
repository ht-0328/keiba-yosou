"""レースの印付けと買い目の組み立てを、複数のプロセスで分けて行う。"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository

from 今週の予想.mark_tickets import MarkTickets

from 印の成績.backtest_marker import BacktestMarker

#: 1つの仕事で印を付けるレースの数。
CHUNK = 400
#: プロセスの中で使う入力（``_prepare`` が入れる）。
_shared: dict[str, object] = {}


def _prepare(tested: pd.DataFrame, places: pd.DataFrame, wins: pd.DataFrame, upset: pd.DataFrame, models: str) -> None:
    """プロセスの最初に1回、入力と印付けの部品を置く（``SearchInputs.load`` と同じ作り）。"""
    state = PlacePriceRepository(Path(models)).load()
    _shared.update(tested=tested, places=places, wins=wins, upset=upset.set_index("race_id"),
                   marker=BacktestMarker(PlacePriceEstimator.from_state(state) if state is not None else None, odds_known=True),
                   tickets=MarkTickets())


def _build(race_ids: list[str], dangers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``race_ids`` のレースに、``dangers`` の消で印を付けて買い目を組む（払戻・オッズはまだ無い）。"""
    tested = _shared["tested"]
    marked = _shared["marker"].mark(tested[tested["race_id"].isin(set(race_ids))], _shared["places"], dangers, _shared["wins"])
    marked = marked.join(_shared["upset"], on="race_id")
    return marked, _shared["tickets"].build(marked)


class RaceVariantWorkers:
    """``build`` は、レースの一覧と消の判定を ``CHUNK`` レースずつに分け、プロセスの集まりで印と買い目を作って、順に返す。
    プロセスの数は ``workers``（省略すると CPU の数 − 2）。入力はプロセスの最初に1回だけ渡す。``close`` で終える。"""

    def __init__(self, tested: pd.DataFrame, places: pd.DataFrame, wins: pd.DataFrame, upset: pd.DataFrame, models: Path,
                 workers: int | None = None) -> None:
        count = workers or max(1, (os.cpu_count() or 2) - 2)
        self._pool = ProcessPoolExecutor(max_workers=count, initializer=_prepare, initargs=(tested, places, wins, upset, str(models)))

    def build(self, race_ids: list[str], dangers: pd.DataFrame):
        """（印の行, 買い目）を、仕事ごとに返す繰り返し。"""
        chunks = [race_ids[start:start + CHUNK] for start in range(0, len(race_ids), CHUNK)]
        parts = [dangers[dangers["race_id"].isin(set(chunk))] for chunk in chunks]
        yield from self._pool.map(_build, chunks, parts)

    def close(self) -> None:
        self._pool.shutdown(wait=True)
