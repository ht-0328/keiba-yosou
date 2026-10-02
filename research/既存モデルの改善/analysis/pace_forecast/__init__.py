"""展開の予想の結果（予想のまとまり P）を、全頭の3着以内の予想に足して、時点ごとに7つの区切りで比べる部品（入口は ``pace_check.py``）。

元の表は、対戦レーティングの確かめ（``head_to_head``）が作った今の本番と同じ材料の学習データ。そこに、予想「展開から着順を予想」の
年ごとの確かめの予測（その年より前だけで学習した展開のモデルの予測）から、予想のパッケージと同じ部品
（``yosou.shared.feature.pace_forecast``）で作った P の 20列を足す。展開の年ごとの予測は、予想のパッケージの ``PaceForecastHistory``（``yosou.race_development``）で読む。区切り・区切りごとの学習・比べ方はこの研究のもの。

| 名前 | 仕事 |
|---|---|
| ``ForecastFiller`` | 展開の予想の年ごとの確かめで、まだ作っていない年（2026年の木曜など）の予測を作り足す |
| ``PaceTable``・``PACE_TABLES`` | P を足す元の表と、時点ごとの足した表の名前 |
| ``PaceTableBuilder`` | 元の表に P の 20列を足す |
| ``PACE_VARIANTS``・``PACE_COMPARISONS`` | 回す作り方と、時点ごとの比べ方（今の予想と、P を足したもの） |
"""

from .forecast_filler import ForecastFiller
from .pace_table_builder import PaceTableBuilder
from .pace_tables import PACE_TABLES, PaceTable, pace_table_named
from .pace_variants import PACE_COMPARISONS, PACE_NAMES, PACE_VARIANTS, PaceComparisonSpec, variant_keyed

__all__ = [
    "ForecastFiller", "PaceTable", "PACE_TABLES", "pace_table_named", "PaceTableBuilder",
    "PACE_COMPARISONS", "PACE_NAMES", "PACE_VARIANTS", "PaceComparisonSpec", "variant_keyed",
]
