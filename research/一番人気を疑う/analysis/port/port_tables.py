"""移したあとの確かめに使う、予想のパッケージで作る学習データの表。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import duckdb

from yosou.form_aptitude_top3.dataset import ability_dataset_builder, pool_dataset_builder
from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, POOL_CATALOG
from yosou.shared.dataset import DatasetBuilder, TrainingPeriod
from yosou.shared.feature import FeatureCatalog

#: 検証・テストの始まり（表を作るときは使わない。区切りは研究「既存モデルの改善」の7つで決める）。
_UNUSED_VALID, _UNUSED_TEST = date(2027, 1, 1), date(2027, 1, 2)


@dataclass(frozen=True)
class PortTable:
    """1つの学習データの表。``builder`` は予想のパッケージの組み立て関数、``period`` は表を作る期間。"""

    name: str
    label: str
    builder: Callable[[duckdb.DuckDBPyConnection], DatasetBuilder]
    catalog: FeatureCatalog
    period: TrainingPeriod


#: 今の材料に券種の支持を足した表（研究「既存モデルの改善」と同じく 2017年から）と、馬の力の材料の表（2012年から。
#: 研究「一番人気を疑う」で、長い期間で学ぶほうが良かったため。本番の木曜のモデルも 2012年から学ぶ）。
PORT_TABLES: tuple[PortTable, ...] = (
    PortTable("form_pool", "今の材料 ＋ 券種の支持", pool_dataset_builder, POOL_CATALOG,
              TrainingPeriod(date(2016, 1, 1), date(2017, 1, 1), _UNUSED_VALID, _UNUSED_TEST)),
    PortTable("form_ability", "馬の力の材料 ＋ 市場の評価", ability_dataset_builder, ABILITY_CATALOG,
              TrainingPeriod(date(2011, 1, 1), date(2012, 1, 1), _UNUSED_VALID, _UNUSED_TEST)),
)


def port_table_named(name: str) -> PortTable:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in PORT_TABLES:
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in PORT_TABLES)}）")
