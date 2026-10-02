"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``FavoriteOnlySelector`` | 1番人気の行だけを残す。``SampleSelector`` を守る |
| ``FinishGroupLabeler`` | 勝利・馬券内・馬券外の3つの列を付ける。``TargetLabeler`` を守る |
| ``PreDeadlineFavorites`` | 締め切り前のオッズで1番人気だった馬の一覧（評価で、確定の1番人気と比べるため） |
| ``FavoritePicks`` | 学習データのうち、学習に使う行と、評価で判定する行（1番人気の選び方ごと）を選ぶ |
| ``dataset_builder()`` | 上の決めごとと特徴量の一覧（``CATALOG``）を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

グループの名前は ``column_names.py``。
"""

from .column_names import GROUPS, IN_THE_MONEY, OUT_OF_THE_MONEY, WIN
from .dataset_assembly import dataset_builder
from .favorite_only_selector import FavoriteOnlySelector
from .favorite_picks import CONFIRMED, PICK, PRE_DEADLINE, FavoritePicks
from .finish_group_labeler import FinishGroupLabeler
from .pre_deadline_favorites import PreDeadlineFavorites

__all__ = [
    "dataset_builder", "FavoriteOnlySelector", "FinishGroupLabeler", "PreDeadlineFavorites", "FavoritePicks",
    "GROUPS", "WIN", "IN_THE_MONEY", "OUT_OF_THE_MONEY", "PICK", "CONFIRMED", "PRE_DEADLINE",
]
