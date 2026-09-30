"""この予想の学習データ・予測用データ（設計書 06・08・10）。

出走の記録を読むクラス（``HistoryRecordsLoader``・``RaceRecordsLoader``）と、データの入れ物（``TrainingData``・
``PredictionData``）は ``yosou.shared.dataset``。ここには、全頭で特徴量を作ってから人気範囲と条件で絞る、
この予想だけの決めごとを置く。

| 名前 | 仕事 |
|---|---|
| ``CustomDataset`` | 学習データ・予測用データを作る。全頭で特徴量を作ってから、人気範囲と条件で絞る |
| ``TrainingDataSelector`` | 全頭の特徴量の表から、人気範囲と条件に当てはまる馬の学習データを作る（研究で何通りも絞るときにも使う） |
| ``PopularityFilter`` | 人気範囲に入る馬を選ぶ |
| ``BinaryTargetLabeler`` | 目的変数（馬券内・馬券外・勝利）を付ける |
| ``AnnouncementCheck`` | 予測の前に、選んだ特徴量に要る今回の情報がそろっているかを確かめる |
| ``OddsBaseline`` | 目的ごとのオッズの基準（モデルの出発点）のロジット |
| ``dataset_columns.py`` | モデルには渡さない列（馬を見分ける列・回収率の材料・予測の期待値の材料）の決まり |
"""

from .announcement_check import AnnouncementCheck
from .binary_target_labeler import BinaryTargetLabeler
from .custom_dataset import CustomDataset
from .odds_baseline import OddsBaseline
from .popularity_filter import PopularityFilter
from .training_data_selector import TrainingDataSelector

__all__ = [
    "AnnouncementCheck", "BinaryTargetLabeler", "CustomDataset", "OddsBaseline", "PopularityFilter",
    "TrainingDataSelector",
]
