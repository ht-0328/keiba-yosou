"""研究で良かった2つの直し方を、予想「近走と適性から3着以内を予想」に移したあとの確かめの部品。

移した作り方の学習データは、予想のパッケージ（``src/yosou/form_aptitude_top3``）の組み立て関数で作る（特徴量の作り方は
この研究に持たない）。区切り・区切りごとの学習は研究「既存モデルの改善」のもの。

| 名前 | 仕事 |
|---|---|
| ``PortTable``・``PORT_TABLES`` | 予想のパッケージで作る学習データの表（今の材料 ＋ 券種の支持・馬の力の材料 ＋ 市場の評価） |
| ``PORT_VARIANTS``・``PORT_COMPARISONS`` | 比べる作り方と、時点ごとの比べ方（今の予想と移した作り方） |
| ``PortPredictionSource`` | 保存した予測に答えと人気を付けて読む |
| ``TableMerge`` | 保存した2つの表を、同じ出走の行でつないで1つにする（当日に馬の力の材料も足す作り方の表） |
| ``PortComparison`` | 区切りごとのログ損失で比べて、採用の基準を満たすかを決める |
"""

from .port_comparison import MIN_BETTER_WINDOWS, PortComparison
from .port_prediction_source import PortPredictionSource
from .port_tables import PORT_TABLES, PortTable, port_table_named
from .port_variants import PORT_COMPARISONS, PORT_VARIANTS, PortComparisonSpec, variant_keyed
from .table_merge import TableMerge

__all__ = [
    "PortComparison", "MIN_BETTER_WINDOWS", "PortPredictionSource", "PortTable", "PORT_TABLES", "port_table_named",
    "PORT_VARIANTS", "PORT_COMPARISONS", "PortComparisonSpec", "variant_keyed", "TableMerge",
]
