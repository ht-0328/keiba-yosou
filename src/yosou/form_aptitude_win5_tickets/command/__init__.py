"""コマンド（fit-payout・predict）。引数を読み、流れ（workflow）や配当の見積もりの式づくりを呼び、結果を表にして出す。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| ``FitPayoutCommand`` | ``fit-payout``: ``--before`` の日より前の WIN5 の当たり組で配当の見積もりの式を作り、保存する |
| ``PredictCommand`` | ``predict``: WIN5 の日を予測し（段階の予算と買う日の線を渡す）、結果を自動で記録する |
| ``Win5ForecastTables`` | 予測の結果を、日のまとめ（判断用の期待値・本命の確率の積・段階・代金）・買う買い目・対象レースごとの全頭の表・予算の候補ごとの表にする |
| ``FormModelsArgument`` | ``predict`` の引数 ``--form-models``（今のモデルの学習済みモデルの置き場所） |

予想に依らない引数（``CommonArguments``・``FigureCacheArgument``・``DevelopmentRootArgument``）は ``yosou.shared.command``。
今のモデルの予測の流れの組み立ては ``yosou.shared.workflow`` の ``FormAptitudePrediction``、材料を作る部品は
``yosou.form_aptitude_materials`` の ``MaterialAttachers``。この予想と今のモデルの名前は ``yosou_name.py``。
"""

from .command_line import CommandLine
from .fit_payout_command import FitPayoutCommand
from .predict_command import PredictCommand

__all__ = ["CommandLine", "FitPayoutCommand", "PredictCommand"]
