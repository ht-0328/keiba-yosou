"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）、予測のときの人気を決める部品
（``PopularityInput``・``PopularityApplier``）、目的変数「3着以内」を付ける部品（``Top3TargetBuilder``）は
``yosou.shared.dataset``。ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``LongshotRule`` | 穴馬の決まりを表す値（頭数ごとの、穴馬の最初の人気と大穴の最初の人気） |
| ``LongshotZone`` | 穴馬の区分（中穴・大穴）を表す値。``--zone`` の書き方を読む |
| ``LongshotSelector`` | 入れる行を選び、「穴馬か」「穴馬の区分」を足す。特徴量のあとに穴馬だけ残す。``SampleSelector`` を守る |
| ``LongshotZoneFilter`` | 予測の結果を、指定された区分の行だけにする |
| ``dataset_builder()`` | 上の決めごとと特徴量の一覧（``CATALOG``）を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

「穴馬か」「穴馬の区分」の列の名前は ``column_names.py``。
"""

from .column_names import IS_LONGSHOT, LONGSHOT_ZONE
from .dataset_assembly import dataset_builder
from .longshot_rule import LongshotRule
from .longshot_selector import LongshotSelector
from .longshot_zone import ZONE_CHOICES, LongshotZone
from .longshot_zone_filter import LongshotZoneFilter

__all__ = [
    "dataset_builder", "LongshotRule", "LongshotZone", "LongshotSelector", "LongshotZoneFilter",
    "IS_LONGSHOT", "LONGSHOT_ZONE", "ZONE_CHOICES",
]
