"""コマンド（train・predict）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 学習データを1回作って（とっておいたものがあれば読んで）、券種ごと・3つの時点ごとに2つのモデルを学習する |
| ``PredictCommand`` | ``predict``: 1レースの、券種ごとの荒れ具合を予測する |
| ``PeriodArguments`` | ``train`` の学習データの期間の引数（地方の既定: ウォームアップ 2016年・学習 2019年から） |
| ``UpsetThresholdTable`` | ``train`` の報告のうち、「中荒れ以上の確率」のしきい値ごとのレース数と実際に中荒れ以上だった割合の表 |

予想に依らない部品（共通の引数 ``CommonArguments``、結果の表 ``ClassTrainingReportTables``・``RacePredictionTable``）は
``yosou.shared.command``。この予想の名前（モデルの置き場所に使う）はパッケージ直下の ``yosou_name.py``（``workflow/`` からも使うため）。
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
