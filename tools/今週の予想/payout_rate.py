"""配当率（配当が中荒れ以上になる確率）を、荒れ具合の予想から出す。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsResolver
from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import AnnouncedOddsRepository
from yosou.upset_level.dataset import race_dataset_builder
from yosou.upset_level.workflow import UPSET_OR_MORE, PredictionWorkflow, model_repositories


class UpsetRunner(Protocol):
    """1レースの券種ごとの荒れ具合の確率を出すもの（``yosou.upset_level`` の ``PredictionWorkflow`` と同じ呼び方）。"""

    def run(self, race_id: str, timing: PredictionTiming) -> pd.DataFrame: ...


class PayoutRate:
    """1レースの配当率 = 荒れ具合の予想（``yosou.upset_level``）が出す4券種（単勝・馬連・3連複・3連単）の「中荒れ以上の確率」の平均（0〜1）。

    設計書「買うレースと買い目を決める」の 03 の 1 の波乱度 U と同じ値で、03 の 5 では配当率と呼ぶ。中荒れの線（券種ごとの払戻の額）は
    荒れ具合の予想の設計書 10 にだけ書いてある。時点（木曜・前日・当日）ごとのモデルを使い、前日・当日は締め切り前のオッズを読む。
    出せないレース（学習済みモデルが無い・出馬表が足りない・オッズがそろっていない など）は None にして、理由を標準エラーに出す
    （予想そのものは止めない）。
    ``models`` は荒れ具合の予想の学習済みモデルの置き場所（``<置き場所>/<券種>/<時点>/``）。``runner`` は DB の接続から予測の流れを作る関数で、
    省略すると ``PredictionWorkflow`` を作る（テストで差し替えるためのもの）。
    """

    def __init__(self, models: Path, runner: Callable[[duckdb.DuckDBPyConnection], UpsetRunner] | None = None) -> None:
        self._models = Path(models)
        self._runner = runner or self._workflow

    def of(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming) -> float | None:
        try:
            prediction = self._runner(con).run(race_id, timing)
        except (ValueError, LookupError, FileNotFoundError) as error:
            print(f"  {race_id}: 配当率（荒れ具合の予想）を出せません: {error}", file=sys.stderr, flush=True)
            return None
        return float(prediction[UPSET_OR_MORE].astype(float).mean())

    def _workflow(self, con: duckdb.DuckDBPyConnection) -> PredictionWorkflow:
        return PredictionWorkflow(race_dataset_builder(con), model_repositories(self._models), OddsResolver(AnnouncedOddsRepository(con)))
