"""流れを進める（オーケストレーション）クラスのうち、どの予想でも同じもの。

| クラス | 仕事 |
|---|---|
| ``TrainingWorkflow`` | 学習の流れ（設計書 05 の図1）。時点ごとに2つのモデルを学習して保存する |
| ``Evaluator`` | 当たり具合を測るクラスの決まり（``TrainingWorkflow`` が受け取る。``ModelEvaluator`` か ``ClassModelEvaluator``） |
| ``ModelSegments`` | 学習データを区分（中穴・大穴、人気帯 など）に分けて、区分ごとに別のモデルで学ぶときの分け方 |
| ``SegmentedTraining`` | 区分ごとに ``TrainingWorkflow`` で学習して保存する（分けない予想は区分が「全体」1つ） |
| ``SegmentedPrediction`` | 予測用データの行を区分に分け、区分ごとのモデルで予測して、2つのモデルの確率と平均を返す |
| ``SegmentedHoldoutPrediction`` | 学習に使っていない期間の学習データを、区分ごとの保存したモデルで予測する |
| ``CalibrationCheck`` | 検証・テストの期間の馬を時点ごとに予測して、確率のずれを測る材料の表を作る |
| ``PredictionWorkflow`` | 1頭ごとの「3着以内」と「1着」の予想の予測の流れ（中央・地方の近走と適性の予想が使う。``PROBABILITY``・``WIN_PROBABILITY`` は確率の列の名前、``PaceSource`` は展開の予測を返す関数の型、``DataAttachment`` は予測用データに列を足す関数の型） |
| ``ExplainedPrediction`` | 予測の結果に、モデルに渡した特徴量の値と特徴量ごとの寄与を添えたもの（``PredictionWorkflow.explain``） |
| ``BacktestWorkflow`` | テスト期間の確かめの流れ（地方の設計書 05 の図4）。保存したモデルでテスト期間を予測し直し、市場の確率と比べ、道具「印の成績」が読む予測の表を書く |
| ``FormAptitudePrediction`` | 今のモデル（予想「近走と適性から3着以内を予想」）の予測の流れを、時点に合わせて組み立てて1レースを予測する（今のモデルのコマンド・道具「今週の予想」・WIN5 の予想が使う） |
| ``FormAptitudeMaterials`` | ``FormAptitudePrediction`` に材料（P・S・T・U・V）を足す関数を渡す部品の決まり（インターフェース。守るクラスは ``yosou.form_aptitude_materials`` の ``MaterialAttachers``）。``MaterialsFactory`` はそれを接続から作る関数の型 |
| ``TimingChooser`` | DB に入っている情報から、今のモデルのいちばん新しい時点（木曜・前日・当日）を選ぶ |
| ``TimingChoice`` | 選んだ時点と、その理由 |

``form_aptitude_timings.py`` は、今のモデルが予測を出す時点・材料を足す時点・モデルの置き場所の名前（``ABILITY_TIMINGS``・``WIN_FOLDER``・``POOL_FREE_FOLDER`` など）。

人気の扱いが違う予想（穴馬・人気馬・荒れ具合）の予測の流れは、予想のパッケージの ``workflow/`` に置く。
"""

from .backtest_workflow import FIELD_SHARE_NAME, MARKET_NAME, BacktestWorkflow
from .calibration_check import CalibrationCheck
from .evaluator import Evaluator
from .explained_prediction import ExplainedPrediction
from .form_aptitude_materials import FormAptitudeMaterials, MaterialsFactory
from .form_aptitude_prediction import FormAptitudePrediction
from .model_segments import WHOLE, ModelSegments
from .prediction_workflow import PROBABILITY, WIN_PROBABILITY, WIN_PROBABILITY_MEMBER, DataAttachment, PaceSource, PredictionWorkflow
from .segmented_holdout_prediction import SegmentedHoldoutPrediction
from .segmented_prediction import AVERAGE, SegmentedPrediction
from .segmented_training import SegmentedTraining
from .timing_choice import TimingChoice
from .timing_chooser import TimingChooser
from .training_workflow import TrainingWorkflow

__all__ = [
    "TrainingWorkflow", "ModelSegments", "WHOLE", "SegmentedTraining", "SegmentedPrediction", "AVERAGE",
    "SegmentedHoldoutPrediction", "CalibrationCheck", "Evaluator",
    "PredictionWorkflow", "ExplainedPrediction", "PROBABILITY", "WIN_PROBABILITY", "WIN_PROBABILITY_MEMBER", "PaceSource", "DataAttachment",
    "BacktestWorkflow", "MARKET_NAME", "FIELD_SHARE_NAME",
    "FormAptitudePrediction", "FormAptitudeMaterials", "MaterialsFactory", "TimingChooser", "TimingChoice",
]
