"""コマンドの部品のうち、予想に依らないもの。

コマンドの入口（``CommandLine``）とサブコマンド（``TrainCommand``・``PredictCommand``）は、
引数と組み立てが予想ごとに違うので、予想のパッケージの ``command/`` にある。

| クラス | 仕事 |
|---|---|
| ``CommonArguments`` | どの予想でも同じ引数（--models --db --format --out） |
| ``TrainingReportTables`` | 学習の結果を表にする |
| ``PredictionTable`` | 予測の結果を、確率の高い順の表にする |

``cell_format.py`` は、表のセルに入れる値の形をそろえる関数。
"""

from .common_arguments import CommonArguments
from .prediction_table import PredictionTable
from .training_report_tables import TrainingReportTables

__all__ = ["CommonArguments", "TrainingReportTables", "PredictionTable"]
