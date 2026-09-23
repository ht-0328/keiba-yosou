"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・08・10）。

学習データ・予測用データを作るクラスそのもの（``RaceDatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``RaceSelector`` | 入れる行（出走馬）を選ぶ（障害・取消を除く、学習データの始まり以降。全頭を残す）。``SampleSelector`` を守る |
| ``BetType`` | 券種を表す値（単勝・馬連・3連複・3連単）。``--bet`` の文字を読む。目的変数の列名とモデルのフォルダ名を持つ |
| ``UpsetLevel`` | 荒れ具合を表す値（固い 0・中荒れ 1・大荒れ 2・超荒れ 3） |
| ``UpsetLevelRule`` | 券種ごとの線引き（3つの額）。線引きの唯一の置き場所 |
| ``UpsetLevelLabeler`` | 払戻から、券種ごとの荒れ具合（4列）を付ける。``RaceTargetLabeler`` を守る |
| ``race_dataset_builder()`` | この予想の部品を渡して、共通の ``RaceDatasetBuilder`` を組み立てる関数（``dataset_assembly.py``） |

評価用の列の名前（払戻）は ``race_column_names.py``。利用者が ``--odds`` で渡すオッズ（``OddsInput``）と、
予測に使うオッズの決め方（``OddsResolver``）は、手本の予想と共通なので ``yosou.shared.dataset``。
"""

from .bet_type import BET_CHOICES, BetType
from .dataset_assembly import race_dataset_builder
from .race_column_names import PAYOUT_COLUMNS, payout_column, payout_popularity_column
from .race_selector import RaceSelector
from .upset_level import UpsetLevel
from .upset_level_labeler import UpsetLevelLabeler
from .upset_level_rule import THRESHOLDS, UpsetLevelRule

__all__ = [
    "race_dataset_builder", "RaceSelector", "BetType", "BET_CHOICES", "UpsetLevel",
    "UpsetLevelRule", "THRESHOLDS", "UpsetLevelLabeler",
    "PAYOUT_COLUMNS", "payout_column", "payout_popularity_column",
]
