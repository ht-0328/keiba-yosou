"""学習データを作って pickle にとっておく。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import duckdb
import pandas as pd

from yosou.local_track_bias import LocalBiasHistory
from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.track_bias import BiasRunRepository
from yosou.upset_level.dataset import UpsetLevelRule

from ..feature import race_slopes_table
from .dataset_assembly import local_race_dataset_builder

#: 元DB の接続を開くコンテキストマネージャを返す関数（``lambda: db.open_db(path, default=db.LOCAL)``）。
ConnectionFactory = Callable[[], AbstractContextManager[duckdb.DuckDBPyConnection]]


class TrainingDataCache:
    """学習データ（1行 = 1レース。当日の馬場傾向のレースの値 U つき）を作って ``folder`` に pickle で書く。同じ期間のファイルがあれば読むだけ。

    作るのに 30〜60分かかる（1頭ごとの特徴量を 2016年からの全出走で作る）ので、``train`` は2回目からこれを読む。
    新しい年の成績がたまって学び直すときは ``rebuild=True`` で作り直す。
    U は、学習データでは年ごとのリーク防止（``LocalBiasHistory``。その年の1月1日より前のレースだけで作った過去の傾きの表と、
    そのレースより前に終わったレースの傾き）で付ける（設計書 11 の 9）。``rule`` は線引き（省略すると地方の線引き）。
    """

    def __init__(self, folder: Path, rule: UpsetLevelRule | None = None) -> None:
        self._folder = Path(folder)
        self._rule = rule

    def path(self, period: TrainingPeriod) -> Path:
        """とっておくファイル。中身はウォームアップと学習データの始まりで決まる（検証・テストの区切りは学習のときに分ける）。"""
        return self._folder / f"学習データ-{period.warmup_first_day.isoformat()}-{period.train_first_day.isoformat()}.pkl"

    def load_or_build(self, con_factory: ConnectionFactory, period: TrainingPeriod, *, rebuild: bool = False) -> TrainingData:
        path = self.path(period)
        if path.exists() and not rebuild:
            return pd.read_pickle(path)
        with con_factory() as con:
            runs = BiasRunRepository(con).read(period.warmup_first_day)
            slopes = race_slopes_table(LocalBiasHistory().of(PredictionTiming.RACE_DAY, runs))
            data = local_race_dataset_builder(con, slopes, self._rule).build_training_data(period)
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle(data, path)
        return data
