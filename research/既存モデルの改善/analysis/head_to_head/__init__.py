"""対戦レーティング（予想のまとまり O）を、全頭の3着以内の予想に足して、時点ごとに7つの区切りで比べる部品（入口は ``h2h_check.py``）。

元の表は予想のパッケージ（``src/yosou/form_aptitude_top3``）の組み立て関数で作った今の本番と同じ学習データ。そこに、予想のパッケージと
同じ部品（``yosou.shared.feature.head_to_head``）で作った対戦レーティングの7列を足す。区切り・区切りごとの学習はこの研究のもの。

| 名前 | 仕事 |
|---|---|
| ``BaseTable``・``BASE_TABLES`` | 元の表（馬の力の材料・今の材料 ＋ 券種の支持）と、対戦レーティングを足した表の名前 |
| ``RatedTableBuilder`` | 元の表に対戦レーティングの7列を足す |
| ``H2H_VARIANTS``・``H2H_COMPARISONS`` | 比べる作り方と、時点ごとの比べ方（今の予想と、対戦レーティングを足したもの） |
| ``PredictionTruth`` | 保存した予測に答えと人気を付けて読む |
| ``TimingComparison`` | 区切りごとのログ損失で比べて、採用の基準を満たすかを決める |
"""

from .base_table import BASE_TABLES, BaseTable, base_table_rated
from .h2h_variants import H2H_COMPARISONS, H2H_NAMES, H2H_VARIANTS, TimingComparisonSpec, variant_keyed
from .prediction_truth import SCORE, PredictionTruth
from .rated_table_builder import RatedTableBuilder
from .timing_comparison import MIN_BETTER_WINDOWS, TimingComparison

__all__ = [
    "BaseTable", "BASE_TABLES", "base_table_rated", "RatedTableBuilder",
    "H2H_VARIANTS", "H2H_COMPARISONS", "H2H_NAMES", "TimingComparisonSpec", "variant_keyed",
    "PredictionTruth", "SCORE", "TimingComparison", "MIN_BETTER_WINDOWS",
]
