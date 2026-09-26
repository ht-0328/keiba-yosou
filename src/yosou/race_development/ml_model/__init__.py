"""この予想のモデル（設計書 03・04 の「ml_model/」・12・13）。二値分類と多クラス分類は共通の部品（``yosou.shared.ml_model``）を使う。

| クラス | 仕事 |
|---|---|
| ``WithinRaceModel`` | 二値のモデル1つを包み、確率をレースの中で合計 1 にそろえる（① 先頭・⑦ 1着） |
| ``LightGbmWithinRaceModel``・``CatBoostWithinRaceModel`` | 上のクラスで、中のモデルを LightGBM・CatBoost にしたもの |
| ``RaceSoftmax`` | raw スコアを温度で割り、レースごとに合計 1 の確率にする |
| ``TemperatureFitter`` | 温度の候補から、レースごとのログ損失がいちばん小さいものを選ぶ |
| ``ValidationHalves`` | 検証データを、開催日で前半（早期終了）と後半（温度・λ）に分ける |
| ``RegressionModel`` | 回帰の2つのモデルに共通の決まり（インターフェース） |
| ``LightGbmRegressionModel``・``CatBoostRegressionModel`` | ④ 4コーナーの位置・⑤ 上がりの速さの回帰 |
| ``RegressionEnsemble`` | 2つの回帰の値を平均する |
| ``QuantileModel`` | 分位点回帰の2つのモデルに共通の決まり（インターフェース） |
| ``LightGbmQuantileModel``・``CatBoostQuantileModel`` | ③ 前半タイム・⑥ 後半タイムの基準との差の分位点回帰（10%・50%・90%） |
| ``QuantileEnsemble`` | 2つの分位点の値を平均し、小さい順に並べ直す |
| ``LightGbmRegressor``・``CatBoostRegressor`` | 回帰と分位点回帰の中身（ライブラリの回帰のモデル1つとエンコーダー） |
| ``OrderProbability`` | 1着の確率から、3連単の並びの確率と、各馬の 2着以内・3着以内の確率を出す（Harville の式） |
| ``OrderLambdaFitter`` | 2着・3着の割り当てのならしの指数 λ を、検証データで決める |
| ``FinishForecaster`` | ⑦ のアンサンブルと λ を持ち、各馬の 1着・2着以内・3着以内の確率を出す |
"""

from .catboost_quantile_model import CatBoostQuantileModel
from .catboost_regression_model import CatBoostRegressionModel
from .catboost_regressor import CatBoostRegressor
from .catboost_within_race_model import CatBoostWithinRaceModel
from .finish_forecaster import LAMBDA_FILE, TOP2, TOP3, WIN, FinishForecaster
from .lightgbm_quantile_model import QUANTILES, LightGbmQuantileModel
from .lightgbm_regression_model import LightGbmRegressionModel
from .lightgbm_regressor import LightGbmRegressor
from .lightgbm_within_race_model import LightGbmWithinRaceModel
from .order_lambda_fitter import OrderLambdaFitter
from .order_probability import OrderProbability
from .quantile_ensemble import QuantileEnsemble
from .quantile_model import QuantileModel
from .race_softmax import RaceSoftmax
from .regression_ensemble import RegressionEnsemble
from .regression_model import RegressionModel
from .temperature_fitter import TemperatureFitter
from .validation_halves import ValidationHalves
from .within_race_model import WithinRaceModel

__all__ = [
    "WithinRaceModel", "LightGbmWithinRaceModel", "CatBoostWithinRaceModel", "RaceSoftmax", "TemperatureFitter",
    "ValidationHalves", "RegressionModel", "LightGbmRegressionModel", "CatBoostRegressionModel", "RegressionEnsemble",
    "QuantileModel", "LightGbmQuantileModel", "CatBoostQuantileModel", "QuantileEnsemble", "QUANTILES",
    "LightGbmRegressor", "CatBoostRegressor", "OrderProbability", "OrderLambdaFitter", "FinishForecaster",
    "LAMBDA_FILE", "WIN", "TOP2", "TOP3",
]
