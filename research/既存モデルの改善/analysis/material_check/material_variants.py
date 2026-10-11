"""材料を足した作り方と、比べる相手（今の本番のモデルの予測）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.dataset import TOP3
from yosou.shared.feature import PredictionTiming

from ..variants import ModelVariant
from .current_production import CURRENT_PRODUCTION, CurrentProduction
from .material import Material
from .material_tables import MaterialTable, material_tables


@dataclass(frozen=True)
class MaterialComparisonSpec:
    """1つの時点・1つの目的変数の比べ方。``current`` は今の本番のモデル（その予測が比べる相手）、``table`` は読む表、
    ``added`` はその表で学ぶ、今の本番の列に材料を足した作り方。"""

    material: Material
    current: CurrentProduction
    table: MaterialTable
    added: ModelVariant

    @property
    def key(self) -> str:
        return self.added.key

    @property
    def timing(self) -> PredictionTiming:
        return self.current.timing

    @property
    def label(self) -> str:
        return self.current.label

    @property
    def current_name(self) -> str:
        return f"今の予想（{self.current.target}・{self.timing.label}）"


def material_comparisons(material: Material) -> tuple[MaterialComparisonSpec, ...]:
    """その材料の比べ方（確かめる時点 × 3着以内・1着。前日が道具「印の成績」の既定なので先に、3着以内を先に、1着をあとに）。"""
    tables = {table.base: table for table in material_tables(material)}
    return tuple(_spec(material, current, tables[current.base_table])
                 for current in CURRENT_PRODUCTION if current.timing in material.timings)


def _spec(material: Material, current: CurrentProduction, table: MaterialTable) -> MaterialComparisonSpec:
    prefix = material.key if current.label == TOP3 else f"{material.key}-win"
    key = f"{prefix}-{current.timing.value}"
    added = ModelVariant(table.name, key, f"今の予想 ＋ {material.label}（{current.target}・{current.timing.label}）",
                         current.columns + material.names, uses_baseline=current.uses_baseline, timing=current.timing)
    return MaterialComparisonSpec(material, current, table, added)


def comparison_keyed(material: Material, key: str) -> MaterialComparisonSpec:
    """保存する名前（``<材料>-<時点>``・``<材料>-win-<時点>``）から引く。知らなければ ``ValueError``。"""
    for spec in material_comparisons(material):
        if spec.key == key:
            return spec
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(spec.key for spec in material_comparisons(material))}）")
