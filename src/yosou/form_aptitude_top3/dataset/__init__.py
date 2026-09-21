"""学習データ・予測用データを作る（設計書 06 の図1・08・10）。

| クラス | 仕事 |
|---|---|
| ``DatasetBuilder`` | 入口。学習データか予測用データを作る。下のクラスを順に呼ぶだけ |
| ``TrainingData``・``PredictionData`` | 学習データ・予測用データの表（1行 = 1頭） |
| ``HistoryRecordsLoader`` | 学習用に、ある日以降の全部の出走の記録を集める |
| ``RaceRecordsLoader`` | 予測用に、1レースの出走馬の記録を集める（速報を反映する） |
| ``EntryRecordsLoader`` | リポジトリを順に呼んで、対象の出走の記録を集める |
| ``AnnouncedWeightApplier`` | 速報の馬体重を、出走の行に反映する |
| ``ScratchApplier`` | 速報の出走取消・競走除外を、出走の行に反映する |
| ``RunnerSelector`` | 入れる行を選ぶ（障害・取消を除く、2024年1月以降） |
| ``TargetBuilder`` | 目的変数（3着以内・1着）を付ける |
| ``RequiredInfoCheck`` | 予測に要る情報（馬番・馬場状態・馬体重）が DB にあるかを確かめる |
| ``PeriodSplitter``・``SplitData`` | 学習データを時期で、学習・検証・テストに分ける |

列の名前（レースID・3着以内 など）は ``column_names.py``。
"""

from .column_names import HORSE_ID, HORSE_NAME, HORSE_NO, RACE_DATE, RACE_ID, TOP3, WIN
from .dataset_builder import DatasetBuilder
from .period_splitter import TEST_FIRST_DAY, VALID_FIRST_DAY, PeriodSplitter
from .prediction_data import PredictionData
from .split_data import SplitData
from .training_data import TrainingData

__all__ = [
    "DatasetBuilder", "TrainingData", "PredictionData", "PeriodSplitter", "SplitData",
    "VALID_FIRST_DAY", "TEST_FIRST_DAY",
    "RACE_ID", "RACE_DATE", "HORSE_ID", "HORSE_NO", "HORSE_NAME", "TOP3", "WIN",
]
