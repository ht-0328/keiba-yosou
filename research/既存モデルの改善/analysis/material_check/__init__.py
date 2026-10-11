"""新しい材料（予想のまとまり）を全頭の予想に足して、時点ごと・目的変数ごとに7つの区切りで今の本番と比べる部品（入口は ``material_check.py``）。

展開スコアの確かめ（``development_score``）と同じ流れを、材料を差し替えられる形にしたもの。元の表は入口⑬が作った、今の本番の列を全部持つ表
（``tables/dscore_*``。P・S、当日の1着は Q も持つ）。今の本番の6つのモデル（時点 × 3着以内・1着）の列と予測は ``current_production.py`` にだけ書く。
材料を足すには、予想のパッケージに部品（特徴量の一覧・足す部品・外す部品）を作り、ここに ``MaterialTableBuilder`` の形のクラスと ``MATERIALS`` の1行を足す。

| 名前 | 仕事 |
|---|---|
| ``CurrentProduction``・``CURRENT_PRODUCTION`` | 今の本番のモデル（時点 × 目的変数）の列と、7つの区切りで学んだ予測の置き場所。比べる相手 |
| ``Material``・``MATERIALS`` | 確かめる材料（名前・列・足し方・足す時点）の一覧 |
| ``MaterialTableBuilder`` | 元の表に材料を足す部品の形（材料ごとに1つ作る） |
| ``AbilityScoreTableBuilder`` | 能力スコア（T）を足す（元の表の能力指数と斤量から。元DB は要らない） |
| ``TrackBiasTableBuilder`` | トラックバイアスの補正（U）を足す（元DB の全出走から傾きを出し、年ごとの確かめの展開の予測④と、その年より前の過去の傾きで） |
| ``WeightDiscountTableBuilder`` | 馬体重の表の割引（V）を足す（元DB の全出走から、年ごとに「その年より前のレースだけで作った表 W」を引く） |
| ``MaterialTable``・``material_tables`` | 材料を足した表の名前（材料 × 元の表） |
| ``MaterialComparisonSpec``・``material_comparisons`` | 時点と目的変数ごとの比べ方（今の本番と、材料を足した作り方） |
"""

from .ability_score_table_builder import AbilityScoreTableBuilder
from .current_production import CURRENT_PRODUCTION, PAYBACK_RESEARCH, THIS_RESEARCH, CurrentProduction, current_production
from .material import Material
from .material_table_builder import MaterialTableBuilder
from .material_tables import MaterialTable, material_table_named, material_tables
from .material_variants import MaterialComparisonSpec, comparison_keyed, material_comparisons
from .materials import MATERIALS, material_named
from .track_bias_table_builder import TrackBiasTableBuilder
from .weight_discount_table_builder import WeightDiscountTableBuilder

__all__ = [
    "CurrentProduction", "CURRENT_PRODUCTION", "current_production", "THIS_RESEARCH", "PAYBACK_RESEARCH",
    "Material", "MATERIALS", "material_named", "MaterialTableBuilder", "AbilityScoreTableBuilder", "TrackBiasTableBuilder",
    "WeightDiscountTableBuilder",
    "MaterialTable", "material_tables", "material_table_named",
    "MaterialComparisonSpec", "material_comparisons", "comparison_keyed",
]
