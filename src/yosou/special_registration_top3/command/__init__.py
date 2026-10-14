"""コマンド（入口と、この予想のサブコマンド・表。共通の部品は ``yosou.shared.command``）。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンド（train・predict・backtest・registrations）を実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 特別登録の時点の 3着以内と1着のモデルを学習して保存する |
| ``PredictCommand`` | ``predict``: 1レース（か ``--all`` で1日の全レース）の登録馬の全員を予測する |
| ``BacktestCommand`` | ``backtest``: 7つの区切りで学習し直し、テスト期間の特別競走で当たり具合を測る |
| ``RegistrationsCommand`` | ``registrations``: 登録馬の全員に予測を出し、出走した馬の結果で当たり具合を確かめる |
| ``PeriodArguments`` | 学習データの期間の引数（``--warmup-from`` ``--train-from`` ``--valid-from`` ``--test-from``） |
| ``RegistrationPredictionTable`` | 登録馬の予測の結果を、確率の高い順の表にする（馬番・オッズ・期待値の列は無い） |
| ``WindowedBacktestTables`` | 7つの区切りでの確かめの結果を表にする |
| ``RegistrationCheckTables`` | 登録馬の確かめの結果を表にする |
| ``YOSOU_NAME`` | この予想の名前（パッケージ直下の ``yosou_name.py``。workflow/ からも使うので command/ には置かない） |
"""

from .backtest_command import BacktestCommand
from .command_line import CommandLine
from .period_arguments import PeriodArguments
from .predict_command import PredictCommand
from .registration_check_tables import RegistrationCheckTables
from .registration_prediction_table import RegistrationPredictionTable
from .registrations_command import RegistrationsCommand
from .train_command import SUBJECT, TrainCommand
from .windowed_backtest_tables import WindowedBacktestTables
from ..yosou_name import YOSOU_NAME

__all__ = [
    "CommandLine", "TrainCommand", "PredictCommand", "BacktestCommand", "RegistrationsCommand", "PeriodArguments",
    "RegistrationPredictionTable", "WindowedBacktestTables", "RegistrationCheckTables", "YOSOU_NAME", "SUBJECT",
]
