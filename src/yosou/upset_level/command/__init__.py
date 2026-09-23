"""コマンド（train・predict）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、元DB を開いて、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 学習データを1回作り、券種ごとに学習する。``--bet`` で券種を絞れる |
| ``PredictCommand`` | ``predict``: 1レースの、券種ごとの荒れ具合を予測する。``--odds`` で全頭のオッズを渡す |

予想に依らない部品（共通の引数 ``CommonArguments``、結果の表 ``ClassTrainingReportTables``・``RacePredictionTable``）は
``yosou.shared.command``。この予想の名前（モデルの置き場所に使う）は ``yosou_name.py``。
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
