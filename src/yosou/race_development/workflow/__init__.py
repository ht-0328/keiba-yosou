"""学習・予測・年ごとの確かめの流れ（設計書 04 の「workflow/」・05）。流れのクラスは、ほかのクラスを順に呼ぶだけで、自分では計算しない。

| 名前 | 仕事 |
|---|---|
| ``DevelopmentModelKind``・``KindSpec`` | 7つの予想と比べる基準の値と、その決めごと（目的変数・特徴量の一覧・モデルの種類・予測の列） |
| ``ModelFamily`` | モデルの種類（レースの中でそろえる二値・多クラス・分位点回帰・回帰） |
| ``ForecastGroup`` | 3つの組（前半・後半・着順）と、組ごとの学習データの最初の年 |
| ``WalkForwardSchedule``・``YearPeriod`` | 年ごとに学習し直すときの、学習・検証・予測の期間 |
| ``KindStacker`` | 1頭ごと（1レースごと）のデータを、予想の特徴量の一覧に合わせ、前の組の予測（S・T）の列を足す（学習と予測で同じ） |
| ``KindDatasets`` | 1頭ごと・1レースごとの学習データから、予想ごとの学習データ（S・T を足したもの）を作る |
| ``KindTrainer`` | 1つの予想の、LightGBM と CatBoost のモデルを学習する |
| ``KindForecaster`` | 1つの予想の2つのモデルで予測し、予測の列の表にする |
| ``GroupFitter`` | 1つの組の予想を、決めた期間で学習し、予測する年を予測する（⑦ は λ も決める） |
| ``WalkForwardPredictor`` | 前の組の「学習に使っていない予測」を年ごとに作り、残す |
| ``RaceBetting`` | 1レースの着順の確率から、印と3つの買い方の買い目を作る |
| ``YearBetting`` | 1年ぶんのレースの買い目を作り、払戻で精算する |
| ``YearMarket`` | 1年ぶんの、7券種の確定オッズと払戻を読む |
| ``BacktestFrames`` | 学習データと予測から、買い目と当たり具合の元になる表を作る |
| ``DatasetLoader`` | 元DB から1頭ごと・1レースごとの学習データを作る（前に作ったものがあれば読む） |
| ``KindModelStore`` | 予想ごと・時点ごとの学習済みモデル（⑦ は λ も）を読み書きする |
| ``DevelopmentTrainingWorkflow``・``SavedModel`` | 学習の流れ。予測に使う最新の年のモデルを、時点ごとに学習して保存する |
| ``DevelopmentPredictionWorkflow``・``DevelopmentForecast`` | 予測の流れと、1レースの予測の入れ物（印と印どおりの買い目まで） |
| ``BacktestWorkflow``・``BacktestReport`` | 年ごとの確かめの流れと、その結果の入れ物 |
"""

from .backtest_report import BacktestReport
from .backtest_workflow import TIMING, BacktestWorkflow
from .dataset_loader import DatasetLoader
from .development_forecast import DevelopmentForecast
from .development_model_kind import DevelopmentModelKind, KindSpec
from .development_prediction_workflow import DevelopmentPredictionWorkflow
from .development_training_workflow import DevelopmentTrainingWorkflow, SavedModel
from .forecast_group import ForecastGroup
from .group_fitter import ORDER_LAMBDA, GroupFitter
from .kind_datasets import KindDatasets
from .kind_forecaster import KindForecaster
from .kind_model_store import KindModelStore
from .kind_stacker import KindStacker
from .kind_trainer import KindTrainer
from .model_family import ModelFamily
from .race_betting import RaceBetting
from .walk_forward_predictor import WalkForwardPredictor
from .walk_forward_schedule import WalkForwardSchedule, YearPeriod
from .year_betting import YearBetting
from .year_market import YearMarket

__all__ = [
    "DevelopmentModelKind", "KindSpec", "ModelFamily", "ForecastGroup", "WalkForwardSchedule", "YearPeriod",
    "KindDatasets", "KindTrainer", "KindForecaster", "GroupFitter", "WalkForwardPredictor", "RaceBetting",
    "YearBetting", "YearMarket", "BacktestWorkflow", "BacktestReport", "ORDER_LAMBDA", "TIMING",
    "KindStacker", "DatasetLoader", "KindModelStore", "DevelopmentTrainingWorkflow", "SavedModel",
    "DevelopmentPredictionWorkflow", "DevelopmentForecast",
]
