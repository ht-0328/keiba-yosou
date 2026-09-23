"""過去で学習して次の期間を予想する検証（ウォークフォワード）を回し、予測を残す。

区切り（``windows/``）ごとに、作り方（``variants/``）の学習データで LightGBM と CatBoost を学習し、
検証期間とテスト期間の予測（2つのモデルの確率と、その平均）を表にして残す。学ぶのは予想のパッケージの
モデルのクラス（``yosou.shared.ml_model``）そのもので、ハイパーパラメータも予想の初期値のまま。

| 名前 | 仕事 |
|---|---|
| ``WindowTrainer`` | 1つの区切り・1つの作り方で学習し、検証とテストの予測を返す（1頭ごとの予想） |
| ``PredictionFrame`` | モデルごとの確率から、予測の表（ID・確率・区切り・区分）を作る |
| ``PredictionStore`` | 予測の表と学習の記録を、予想 × 作り方 ごとのファイルに書く・読む |
| ``WalkForwardRunner`` | 区切りを順に回して、予測の表と学習の記録をまとめる |
| ``UpsetWindowTrainer`` | 荒れ具合の予想（現行の作り方）を、1つの区切りで券種ごとに学習し、4クラスの確率を返す |
"""

from .prediction_frame import PART, PART_TEST, PART_VALID, PREDICTION_COLUMN, SEGMENT, WINDOW, PredictionFrame
from .prediction_store import PredictionStore
from .walk_forward_runner import WalkForwardRunner
from .upset_window_trainer import BET, UpsetWindowTrainer
from .window_trainer import WindowTrainer

__all__ = [
    "WindowTrainer", "PredictionFrame", "PredictionStore", "WalkForwardRunner",
    "PART_VALID", "PART_TEST", "PREDICTION_COLUMN", "PART", "WINDOW", "SEGMENT",
    "UpsetWindowTrainer", "BET",
]
