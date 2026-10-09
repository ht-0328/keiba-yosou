"""距離の変更の傾向（予想のまとまり R）を、全頭の予想（3着以内・1着のモデル）に足して、時点ごとに7つの区切りで比べる部品（入口は ``distance_check.py``）。

元の表は、今の本番のモデルを7つの区切りで学んだときの表（木曜 ``pace_thursday``・前日 ``h2h_ability``・当日 ``h2h_pool_ability``、
当日の1着は研究「回収率100超の施策」の ``finish_pool_ability``）。そこに、予想のパッケージの ``DistanceChangeRecordsLoader``
（事実表から、開催日の前日までの記録だけで数える）で読んだ R の 7列を足す。区切り・区切りごとの学習・比べ方はこの研究のもの。

| 名前 | 仕事 |
|---|---|
| ``DistanceTable``・``DISTANCE_TABLES`` | R を足す元の表と、足した表の名前 |
| ``DistanceTableBuilder`` | 元の表に R の 7列を足す |
| ``DistanceVariantSpec``・``DISTANCE_VARIANTS`` | 時点ごと・目的変数ごとの作り方と、比べる相手（今の本番のモデルの予測） |
"""

from .distance_table_builder import DistanceTableBuilder
from .distance_tables import DISTANCE_TABLES, PAYBACK_RESEARCH, THIS_RESEARCH, DistanceTable, distance_table_named
from .distance_variants import DISTANCE_VARIANTS, DistanceVariantSpec, spec_keyed

__all__ = [
    "DistanceTable", "DISTANCE_TABLES", "distance_table_named", "DistanceTableBuilder", "THIS_RESEARCH", "PAYBACK_RESEARCH",
    "DistanceVariantSpec", "DISTANCE_VARIANTS", "spec_keyed",
]
