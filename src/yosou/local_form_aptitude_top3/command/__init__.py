"""コマンド（train・predict・backtest）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| ``TrainCommand`` | ``train``: 学習する（3つの時点 × 3着以内・1着 と、当日の券種オッズなし） |
| ``PredictCommand`` | ``predict``: 1レースを予測する |
| ``BacktestCommand`` | ``backtest``: テスト期間の確かめ（保存したモデルで予測し直し、市場の確率と比べ、印の成績が読む予測の表を書く） |
| ``PeriodArguments`` | train と backtest に共通の、学習データの期間の引数 |

予想に依らない部品（共通の引数 ``CommonArguments``、結果の表 ``TrainingReportTables``・``PredictionTable``・``BacktestReportTables``）は
``yosou.shared.command``。この予想の名前（モデルの置き場所に使う）は ``yosou_name.py``。
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
