"""コマンド（train・predict）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、元DB を開いて、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 学習する |
| ``PredictCommand`` | ``predict``: 1レースの穴馬を予測する（``--pops`` で全頭の人気を、``--zone`` で絞る区分を渡す） |

予想に依らない部品（共通の引数 ``CommonArguments``、結果の表 ``TrainingReportTables``・``PredictionTable``）は
``yosou.shared.command``。この予想の名前（モデルの置き場所に使う）は ``yosou_name.py``。
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
