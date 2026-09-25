"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``FavoriteOnlySelector`` | 1番人気の行だけを残す。``SampleSelector`` を守る |
| ``FinishGroupLabeler`` | 勝利・馬券内・馬券外の3つの列を付ける。``TargetLabeler`` を守る |
| ``dataset_builder()`` | 上の決めごとと特徴量の一覧（``CATALOG``）を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

グループの名前は ``column_names.py``。
"""

from .column_names import GROUPS, IN_THE_MONEY, OUT_OF_THE_MONEY, WIN
from .dataset_assembly import dataset_builder
from .favorite_only_selector import FavoriteOnlySelector
from .finish_group_labeler import FinishGroupLabeler

__all__ = [
    "dataset_builder", "FavoriteOnlySelector", "FinishGroupLabeler",
    "GROUPS", "WIN", "IN_THE_MONEY", "OUT_OF_THE_MONEY",
]
