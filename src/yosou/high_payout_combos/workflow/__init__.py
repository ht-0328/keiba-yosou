"""流れを進める（オーケストレーション）。ほかのフォルダのクラスを決まった順に呼んで、データを受け渡す。

| 名前 | 仕事 |
|---|---|
| ``TableWorkflow`` | 過去のレースの組の表を、月ごとに作って年ごと・券種ごとのファイルに書く。結果は ``TableYearResult`` |
| ``WalkForwardWorkflow`` | 年ごとに学んで次の年を予測し、予測を保存する（確かめ用）。結果は ``WalkYearResult`` |
| ``ProductionTraining`` | 本番のモデルを学習して保存する。結果は ``ProductionTrainingResult`` |
| ``HighPayoutPredictor`` | 本番の予測の入口。1レースの馬ごとの表と板から、対象の組の当たる確率を出す |
| ``YearSamples`` | 年ごとの学習の行（外れを間引いて重みつき）を、保存した組の表から作る |
| ``TicketModelTrainer`` | 1つの券種の LightGBM と CatBoost を学習する |
| ``TablePrediction`` | 組の表の全部の行に、当たる確率（2つの平均とモデルごと）を付ける |
"""

from .high_payout_predictor import PREDICTION_COLUMNS, HighPayoutPredictor
from .production_training import ProductionTraining
from .production_training_result import ProductionTrainingResult
from .table_prediction import TablePrediction
from .table_workflow import TableWorkflow
from .table_year_result import TableYearResult
from .ticket_model_trainer import TicketModelTrainer
from .walk_forward_workflow import WalkForwardWorkflow
from .walk_year_result import WalkYearResult
from .year_samples import YearSamples

__all__ = [
    "TableWorkflow", "TableYearResult", "WalkForwardWorkflow", "WalkYearResult", "ProductionTraining", "ProductionTrainingResult",
    "HighPayoutPredictor", "PREDICTION_COLUMNS", "YearSamples", "TicketModelTrainer", "TablePrediction",
]
