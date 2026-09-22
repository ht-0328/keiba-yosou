"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）と、予測のときの人気を決める部品
（``PopularityInput``・``PopularityApplier``）は ``yosou.shared.dataset``。ここには、この予想だけの決めごとと、
それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``FavoriteRule`` | 人気馬の決まりを表す値（頭数の線引きと、頭数ごとの人気の範囲） |
| ``FavoriteSelector`` | 入れる行を選び、「人気馬か」を足す。特徴量のあとに人気馬だけ残す。``SampleSelector`` を守る |
| ``OutOfTop3TargetBuilder`` | 目的変数（4着以下）を付ける。``TargetLabeler`` を守る |
| ``dataset_builder()`` | 上の決めごとと特徴量の一覧（``CATALOG``）を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

目的変数と「人気馬か」の列の名前は ``column_names.py``。
"""

from .column_names import IS_FAVORITE, OUT_OF_TOP3
from .dataset_assembly import dataset_builder
from .favorite_rule import FavoriteRule
from .favorite_selector import FavoriteSelector
from .out_of_top3_target_builder import OutOfTop3TargetBuilder

__all__ = [
    "dataset_builder", "FavoriteRule", "FavoriteSelector", "OutOfTop3TargetBuilder",
    "OUT_OF_TOP3", "IS_FAVORITE",
]
