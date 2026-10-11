"""材料を足した表の名前（材料 × 元の表）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.feature import FeatureCatalog, PredictionTiming

from ..development_score import score_table_named
from .current_production import CURRENT_PRODUCTION, THIS_RESEARCH, CurrentProduction
from .material import Material


@dataclass(frozen=True)
class MaterialTable:
    """材料を足した表1つ。``base`` は元の表の名前（入口⑬が作った、今の本番の列を全部持つ表）、``base_catalog`` はその特徴量の一覧、
    ``timing`` は材料を作る時点。"""

    name: str
    label: str
    base: str
    base_research: str
    base_catalog: FeatureCatalog
    timing: PredictionTiming
    material: Material

    @property
    def catalog(self) -> FeatureCatalog:
        """材料の列を足した特徴量の一覧。"""
        names = set(self.base_catalog.names)
        return FeatureCatalog(self.base_catalog.features + tuple(feature for feature in self.material.features if feature.name not in names))


def material_tables(material: Material) -> tuple[MaterialTable, ...]:
    """その材料で作る表（確かめる時点の、今の本番の元の表ごとに1つ。同じ元の表は1つにまとめる）。"""
    bases: dict[str, CurrentProduction] = {}
    for current in CURRENT_PRODUCTION:
        if current.timing in material.timings:
            bases.setdefault(current.base_table, current)
    return tuple(_table(material, current) for current in bases.values())


def _table(material: Material, current: CurrentProduction) -> MaterialTable:
    base = score_table_named(current.base_table)
    name = current.base_table.replace("dscore", material.key, 1)
    return MaterialTable(name, f"{base.label} ＋ {material.label}", base.name, THIS_RESEARCH, base.catalog, current.timing, material)


def material_table_named(material: Material, name: str) -> MaterialTable:
    """名前から引く。知らなければ ``ValueError``。"""
    for table in material_tables(material):
        if table.name == name:
            return table
    raise ValueError(f"知らない表です: {name}（{' / '.join(table.name for table in material_tables(material))}）")
