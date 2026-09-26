"""コマンドの引数と、結果の表（設計書 04 の「command/」）。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 時点ごとに7つの予想のモデルを学習して保存する |
| ``PredictCommand`` | ``predict``: 1レースの展開と着順を予測し、印と印どおりの買い目を出す |
| ``BacktestCommand`` | ``backtest``: 年ごとに学習し直して過去のレースを予測し、券種ごと・年ごとの的中率と回収率を出す |
| ``BacktestTables`` | 年ごとの確かめの結果を、表1〜4 と確率の当てはまりの表にする |
"""

from .backtest_command import BacktestCommand
from .backtest_tables import BacktestTables
from .command_line import CommandLine
from .predict_command import PredictCommand
from .train_command import TrainCommand

__all__ = ["CommandLine", "TrainCommand", "PredictCommand", "BacktestCommand", "BacktestTables"]
