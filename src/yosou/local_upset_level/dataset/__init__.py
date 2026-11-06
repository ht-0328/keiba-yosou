"""この予想の、学習データ・予測用データの決めごと（設計書 04・08・10）。

学習データ・予測用データを作るクラスそのもの（``RaceDatasetBuilder``）は ``yosou.shared.dataset``、レースを選ぶ・券種・荒れ具合・
目的変数を付けるクラス（``RaceSelector``・``BetType``・``UpsetLevel``・``UpsetLevelLabeler``）は中央の ``yosou.upset_level.dataset``。
ここには、地方だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``LocalUpsetRule``・``LOCAL_THRESHOLDS`` | 地方の券種ごとの線引き（3連単は 1万・10万・100万円。ほかは 3連単と同じ割合になる額）。線引きの唯一の置き場所 |
| ``local_race_dataset_builder()`` | 地方の部品（事実表・出走別着度数地方・地方の線引き・U のレースの値）を渡して、共通の ``RaceDatasetBuilder`` を組み立てる関数 |
| ``TrainingDataCache`` | 学習データ（U つき）を作って pickle にとっておく。2回目からは読むだけ |
| ``LOCAL_UPSET_WARMUP_FIRST_DAY``・``LOCAL_UPSET_TRAIN_FIRST_DAY`` | 学習データの既定の期間（ウォームアップ 2016年・学習 2019年から） |
"""

from .dataset_assembly import LOCAL_UPSET_TRAIN_FIRST_DAY, LOCAL_UPSET_WARMUP_FIRST_DAY, local_race_dataset_builder
from .local_upset_rule import LOCAL_THRESHOLDS, LocalUpsetRule
from .training_data_cache import TrainingDataCache

__all__ = [
    "local_race_dataset_builder", "LocalUpsetRule", "LOCAL_THRESHOLDS", "TrainingDataCache",
    "LOCAL_UPSET_WARMUP_FIRST_DAY", "LOCAL_UPSET_TRAIN_FIRST_DAY",
]
