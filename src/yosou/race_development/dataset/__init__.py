"""学習データ・予測用データの行を選び、目的変数を付ける（設計書 06・08・10）。

| 名前 | 仕事 |
|---|---|
| ``EarlyRunnerSelector`` | 入れる行を選ぶ（平地・出走した馬の全頭） |
| ``EarlyPositionLabeler`` | ① 先頭と ② 序盤の位置の区分を付ける |
| ``LateLabeler`` | ④ 4コーナーの位置と ⑤ 上がりの速さを付ける |
| ``FinishLabeler`` | ⑦ 1着を付ける |
| ``HorseLabeler`` | 1頭ごとの5つの目的変数を、まとめて付ける（``TargetLabeler`` を守る） |
| ``RaceLabeler`` | ③ ペースの区分・前半タイムの基準との差と、⑥ 後半タイムの基準との差を付ける（``RaceTargetLabeler`` を守る） |
| ``PaceRecordSource`` | レースごとの前半・後半タイムに基準を付けて返す（``RaceResultSource`` を守る） |
| ``horse_dataset_builder()``・``race_dataset_builder()`` | この予想の部品で、共通の ``DatasetBuilder``・``RaceDatasetBuilder`` を組み立てる |
| ``label_names.py`` | 目的変数と評価用の列の名前 |

順位を 0〜1 に直す部品（``RelativeRank``・``EarlyPosition``）と基準の作り方（``PaceBaseline``）は、特徴量の側
（``feature/history/``）にもあるので、そこに置いて、ここから使う（参照の向きは dataset → feature）。
"""

from . import label_names
from .dataset_assembly import horse_dataset_builder, horse_feature_builder, race_dataset_builder
from .early_position_labeler import EarlyPositionLabeler
from .early_runner_selector import EarlyRunnerSelector
from .finish_labeler import FinishLabeler
from .horse_labeler import HorseLabeler
from .late_labeler import LateLabeler
from .pace_record_source import PaceRecordSource
from .race_labeler import RaceLabeler

__all__ = [
    "EarlyRunnerSelector", "EarlyPositionLabeler", "LateLabeler", "FinishLabeler", "HorseLabeler", "RaceLabeler",
    "PaceRecordSource", "horse_dataset_builder", "horse_feature_builder", "race_dataset_builder", "label_names",
]
