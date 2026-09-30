"""コマンド（features・train・predict・evaluate）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| 名前 | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| ``FeaturesCommand`` | ``features``: 選べる特徴量の一覧 |
| ``TrainCommand`` | ``train``: 設定の YAML で学習して保存する |
| ``PredictCommand`` | ``predict``: 保存したモデルで1レースを予想する |
| ``EvaluateCommand`` | ``evaluate``: 未学習のテスト期間で評価する |
| ``CommonOptions`` | サブコマンドに共通の引数（--format・--out・--db・--models） |
| ``TrainingTables`` | 学習の結果（設定の要約・検証期間の成績と回収率）を表にする |
| ``PredictionTable`` | 予測の結果を表にする（道具 ``tools/当日の予想`` も使う） |
"""

from .command_line import CommandLine
from .prediction_table import PredictionTable

__all__ = ["CommandLine", "PredictionTable"]
