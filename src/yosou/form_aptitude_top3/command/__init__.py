"""コマンド（train・predict）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、元DB を開いて、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 学習する |
| ``PredictCommand`` | ``predict``: 1レースを予測する |
| ``TrainPeriodArguments`` | ``train`` の学習データの期間の区切りの引数と、引数から2つの期間（今の材料・馬の力の材料）を作る |

予想に依らない部品（共通の引数 ``CommonArguments``・``FigureCacheArgument``・``DevelopmentRootArgument``、結果の表 ``TrainingReportTables``・
``PredictionTable``）は ``yosou.shared.command``。``predict`` の予測の流れの組み立ては ``yosou.shared.workflow`` の ``FormAptitudePrediction``、
材料を作る部品は ``yosou.form_aptitude_materials`` の ``MaterialAttachers``。この予想の名前（モデルの置き場所に使う）は ``yosou_name.py``。
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
