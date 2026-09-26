"""元DB から1頭ごと・1レースごとの学習データを作る（前に作ったものがあれば読む）。"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod

from ..dataset import horse_dataset_builder, race_dataset_builder
from ..repository import DatasetRepository
from .kind_datasets import KindDatasets

#: 学習データのウォームアップと始まり（設計書 08 の 5・16 の 7）。
WARMUP_FIRST_DAY = date(2016, 1, 1)
TRAIN_FIRST_DAY = date(2017, 1, 1)


class DatasetLoader:
    """2017年1月から ``last_year`` の年末までの、1頭ごと・1レースごとの学習データを作る（ウォームアップは 2016年）。

    元DB を開くのは、学習データを作るあいだだけ。作ったものは ``DatasetRepository`` に、元DB の更新日時と期間と一緒に残し、
    どちらも変わっていなければ、次からは読むだけにする（学習（train）と年ごとの確かめ（backtest）で共有する）。
    ``reuse_saved`` を真にすると、元DB が変わっていても、期間が同じなら前に作ったものを読む（年ごとの確かめの表だけを
    作り直すとき。元DB に最新のレースが足されると、学習データが変わり、前の組の予測をすべて作り直すことになるため）。
    """

    def __init__(self, repository: DatasetRepository, db_path: Path | None,
                 progress: Callable[[str], None] | None = None, reuse_saved: bool = False) -> None:
        self._repository = repository
        self._db_path = db_path
        self._progress = progress or (lambda message: None)
        self._reuse_saved = reuse_saved

    def load(self, last_year: int) -> KindDatasets:
        period = TrainingPeriod(WARMUP_FIRST_DAY, TRAIN_FIRST_DAY, date(last_year + 1, 1, 1), date(last_year + 1, 1, 2))
        database = "" if self._reuse_saved else str(db.resolve_db(self._db_path).stat().st_mtime_ns)
        signature = f"{database}-{period}"
        horses = self._repository.load("horses", signature)
        races = self._repository.load("races", signature)
        if horses is None or races is None:
            horses, races = self._build(period)
            self._repository.save("horses", signature, horses)
            self._repository.save("races", signature, races)
        return KindDatasets(horses, races)

    def _build(self, period: TrainingPeriod) -> tuple[TrainingData, TrainingData]:
        started = time.perf_counter()
        with db.open_db(self._db_path) as con:
            horses = horse_dataset_builder(con).build_training_data(period)
            races = race_dataset_builder(con).build_training_data(period)
        self._progress(f"学習データを作った（{len(horses)}頭・{len(races)}レース、{(time.perf_counter() - started) / 60:.1f}分）")
        return horses, races
