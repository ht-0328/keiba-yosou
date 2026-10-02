"""対戦レーティングを足す元になる、予想のパッケージで作る学習データの表。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import duckdb

from yosou.form_aptitude_top3.dataset import ability_dataset_builder, race_day_dataset_builder
from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.dataset import DatasetBuilder, TrainingPeriod
from yosou.shared.feature import HEAD_TO_HEAD_FEATURES, FeatureCatalog

#: 検証・テストの始まり（表を作るときは使わない。区切りは7つの区切りで決める）。
_UNUSED_VALID, _UNUSED_TEST = date(2027, 1, 1), date(2027, 1, 2)


@dataclass(frozen=True)
class BaseTable:
    """元の表1つ。``builder`` は予想のパッケージの組み立て関数、``period`` は表を作る期間、``rated_name`` は対戦レーティングを足した表の名前。"""

    name: str
    label: str
    builder: Callable[[duckdb.DuckDBPyConnection], DatasetBuilder]
    catalog: FeatureCatalog
    period: TrainingPeriod
    rated_name: str

    @property
    def rated_catalog(self) -> FeatureCatalog:
        """対戦レーティングの7個を足した特徴量の一覧。"""
        return FeatureCatalog(self.catalog.features + HEAD_TO_HEAD_FEATURES)


#: 今の本番と同じ2つの表。木曜・前日のモデルは馬の力の材料（2012年から）、当日のモデルは今の材料に券種の支持と馬の力の材料を
#: 足したもの（2017年から）。研究「一番人気を疑う」の移したあとの確かめ（``port_check.py tables``）と同じ作り方なので、その表があれば読む。
BASE_TABLES: tuple[BaseTable, ...] = (
    BaseTable("form_ability", "馬の力の材料 ＋ 市場の評価（木曜・前日）", ability_dataset_builder, ABILITY_CATALOG,
              TrainingPeriod(date(2011, 1, 1), date(2012, 1, 1), _UNUSED_VALID, _UNUSED_TEST), "h2h_ability"),
    BaseTable("form_pool_ability", "今の材料 ＋ 券種の支持 ＋ 馬の力の材料（当日）", race_day_dataset_builder, RACE_DAY_CATALOG,
              TrainingPeriod(date(2016, 1, 1), date(2017, 1, 1), _UNUSED_VALID, _UNUSED_TEST), "h2h_pool_ability"),
)


def base_table_rated(rated_name: str) -> BaseTable:
    """対戦レーティングを足した表の名前から引く。知らなければ ``ValueError``。"""
    for table in BASE_TABLES:
        if table.rated_name == rated_name:
            return table
    raise ValueError(f"知らない表です: {rated_name}（{' / '.join(table.rated_name for table in BASE_TABLES)}）")
