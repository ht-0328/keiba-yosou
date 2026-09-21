"""コマンド（train・predict）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、元DB を開いて、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 学習する |
| ``PredictCommand`` | ``predict``: 1レースを予測する |
| ``CommonArguments`` | 2つのサブコマンドに共通の引数（--models --db --format --out） |
| ``TrainingReportTables`` | 学習の結果を表にする |
| ``PredictionTable`` | 予測の結果を表にする |
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
