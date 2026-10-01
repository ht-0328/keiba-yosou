"""学習・予測・テスト期間の評価の流れを進める（オーケストレーション。設計書 05）。

流れのクラスは、ほかのフォルダのクラスを決まった順に呼んで、データを受け渡すだけ。結果を表にするのは ``command/``。

| 名前 | 仕事 |
|---|---|
| ``TrainingWorkflow`` | 学習の流れ（設計書 05 の図1）。設定を読む → 学習データを作る → 学ぶ → 検証期間で評価する → 保存する |
| ``PredictionWorkflow`` | 予測の流れ（設計書 05 の図2）。人気とオッズを決める → 予測用データを作る → 確率と期待値を出す |
| ``TestEvaluationWorkflow`` | テスト期間の評価の流れ。保存したモデルで、テスト期間の当たり具合と回収率を出して書く |
| ``EnsembleFitter`` | 学習期間で2つのモデルを学び、検証期間で早期終了を決める（保存はしない。研究の探索でも使う） |
| ``LoadedModel`` | 予想に使う、保存したモデル一式（設定・2つのモデルの平均・複勝の想定払戻倍率） |
| ``TrainedModel`` | 学習の流れの結果（設定・保存先・検証期間の成績） |
"""

from .ensemble_fitter import EnsembleFitter
from .loaded_model import LoadedModel
from .prediction_workflow import PredictionWorkflow
from .test_evaluation_workflow import TestEvaluationWorkflow
from .trained_model import TrainedModel
from .training_workflow import TrainingWorkflow

__all__ = [
    "EnsembleFitter", "LoadedModel", "PredictionWorkflow", "TestEvaluationWorkflow", "TrainedModel",
    "TrainingWorkflow",
]
