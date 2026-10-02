"""コマンド（``python -m yosou.stakes_tendency_top3``）の入口と、サブコマンドごとのクラス。

| 名前 | 仕事 |
|---|---|
| ``CommandLine`` | 引数を読んで、サブコマンドを実行する |
| ``TrainCommand`` | ``train``: 3つの時点ごとに2つのモデルを学習して保存する |
| ``PredictCommand`` | ``predict``: 1レース（重賞）の出走馬ごとの「3着以内に入る確率」を出す |
| ``EvaluateCommand`` | ``evaluate``: 学習に使っていない期間の重賞で、複勝の期待値買いと本命の成績を出す |
| ``YOSOU_NAME`` | この予想の名前（モデルの置き場所に使う） |
"""

from .command_line import CommandLine
from .evaluate_command import EvaluateCommand
from .predict_command import PredictCommand
from .train_command import TrainCommand
from .yosou_name import YOSOU_NAME

__all__ = ["CommandLine", "TrainCommand", "PredictCommand", "EvaluateCommand", "YOSOU_NAME"]
