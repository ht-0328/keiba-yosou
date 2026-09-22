"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``FavoriteRule`` | 人気馬の決まりを表す値（頭数の線引きと、頭数ごとの人気の範囲） |
| ``FavoriteSelector`` | 入れる行を選び、「人気馬か」を足す。特徴量のあとに人気馬だけ残す。``SampleSelector`` を守る |
| ``OutOfTop3TargetBuilder`` | 目的変数（4着以下）を付ける。``TargetLabeler`` を守る |
| ``PopularityInput`` | 利用者が ``--pops`` で渡した「馬番 → 人気」を表す値 |
| ``PopularityApplier`` | 予測に使う人気を決める（渡された人気 → 締め切り前のオッズ → 元DB の人気） |
| ``dataset_builder()`` | 上の決めごとと特徴量の一覧（``CATALOG``）を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

目的変数と「人気馬か」の列の名前は ``column_names.py``。
"""

from .column_names import IS_FAVORITE, OUT_OF_TOP3
from .dataset_assembly import dataset_builder
from .favorite_rule import FavoriteRule
from .favorite_selector import FavoriteSelector
from .out_of_top3_target_builder import OutOfTop3TargetBuilder
from .popularity_applier import PopularityApplier
from .popularity_input import PopularityInput

__all__ = [
    "dataset_builder", "FavoriteRule", "FavoriteSelector", "OutOfTop3TargetBuilder",
    "PopularityInput", "PopularityApplier", "OUT_OF_TOP3", "IS_FAVORITE",
]
