"""コマンドの部品のうち、予想に依らないもの。

コマンドの入口（``CommandLine``）とサブコマンド（``TrainCommand``・``PredictCommand``）は、
引数と組み立てが予想ごとに違うので、予想のパッケージの ``command/`` にある。

| クラス | 仕事 |
|---|---|
| ``CommonArguments`` | どの予想でも同じ引数（--models --db --format --out） |
| ``TrainingReportTables`` | 二値分類の学習の結果を表にする |
| ``ClassTrainingReportTables`` | 多クラス分類の学習の結果を表にする（期間・当たり具合・混同行列・保存したモデル） |
| ``PredictionTable`` | 1頭ごとの予測の結果を、確率の高い順の表にする |
| ``RacePredictionTable`` | レース単位の予測の結果（券種ごと など）を、そのまま表にする |

``cell_format.py`` は、表のセルに入れる値の形をそろえる関数。
"""

from .class_training_report_tables import ClassTrainingReportTables
from .common_arguments import CommonArguments
from .prediction_table import PredictionTable
from .race_prediction_table import RacePredictionTable
from .training_report_tables import TrainingReportTables

__all__ = [
    "CommonArguments", "TrainingReportTables", "ClassTrainingReportTables", "PredictionTable", "RacePredictionTable",
]
