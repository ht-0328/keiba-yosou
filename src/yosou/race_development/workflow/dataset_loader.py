"""元DB から1頭ごと・1レースごと・既存の予想ごとの学習データを作る（前に作ったものがあれば読む）。"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

import duckdb

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod

from ..dataset import horse_dataset_builder, race_dataset_builder
from ..repository import DatasetRepository
from ..tendency import TendencyDatasets, TendencySource
from .kind_datasets import KindDatasets

#: 学習データのウォームアップと始まり（設計書 08 の 5・16 の 7）。元DB は 2011年からあり、前半・後半タイムの基準は
#: ウォームアップの始まりの 1095日前から読むので、2014年からの学習データは、どのレースも3年ぶんの基準で作れる。
WARMUP_FIRST_DAY = date(2013, 1, 1)
TRAIN_FIRST_DAY = date(2014, 1, 1)
#: 元DB のロックを待つ上限（秒）。学習データを作る段と確定オッズを読む段は、ほかの道具が元DB を読み終わるのを待ってから始める
#: （共通の既定の 15秒では、同じマシンで何本も学習を動かしているときに、待ちきれずに止まるため）。
DB_LOCK_WAIT_SECONDS = 3600.0
#: 学習データの作り方の版。元DB の更新日時と期間では表せない作り方（共通の事実表の数え方など）を変えたら書き換え、
#: 前に作った学習データを読まずに作り直させる。
DATASET_VERSION = "2026-09-30"
#: 学習データの名前（ファイル名）→ 元DB への接続から、その学習データを作るクラスを組み立てる関数。
_BUILDERS: dict[str, Callable[[duckdb.DuckDBPyConnection], object]] = {
    "horses": horse_dataset_builder,
    "races": race_dataset_builder,
    **{f"tendency_{source.value}": source.spec.builder for source in TendencySource},
}


class DatasetLoader:
    """2014年1月から ``last_year`` の年末までの学習データを作る（ウォームアップは 2013年）。

    作るのは、展開の予想の1頭ごと・1レースごとの学習データと、傾向の組が学ぶ既存の4つの予想の学習データ
    （それぞれの予想の ``dataset_builder`` で作る）。元DB を開くのは、学習データを作るあいだだけ。
    作ったものは ``DatasetRepository`` に、元DB の更新日時と期間と一緒に残し、どちらも変わっていなければ、
    次からは読むだけにする（学習（train）と年ごとの確かめ（backtest）で共有する）。
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
        signature = f"{database}-{DATASET_VERSION}-{period}"
        saved = {name: self._repository.load(name, signature) for name in _BUILDERS}
        missing = [name for name, data in saved.items() if data is None]
        if missing:
            saved.update(self._build(missing, period, signature))
        tendency = TendencyDatasets({source: saved[f"tendency_{source.value}"] for source in TendencySource})
        return KindDatasets(saved["horses"], saved["races"], tendency)

    def _build(self, names: list[str], period: TrainingPeriod, signature: str) -> dict[str, TrainingData]:
        """``names`` の学習データを元DB から作り、残す。"""
        started = time.perf_counter()
        with db.open_db(self._db_path, lock_timeout=DB_LOCK_WAIT_SECONDS) as con:
            built = {name: _BUILDERS[name](con).build_training_data(period) for name in names}
        for name, data in built.items():
            self._repository.save(name, signature, data)
        sizes = "・".join(f"{name} {len(data)}行" for name, data in built.items())
        self._progress(f"学習データを作った（{sizes}、{(time.perf_counter() - started) / 60:.1f}分）")
        return built
