"""1つの時点・1つのモデルの当たり具合。"""

from __future__ import annotations

from dataclasses import dataclass

from ..feature import PredictionTiming


@dataclass(frozen=True)
class Evaluation:
    """当たり具合の値。ログ損失と Brier は小さいほど、AUC と ``top_pick_place_rate`` は大きいほど良い。

    ``tree_count`` は早期終了で残った木の数（アンサンブルの行では None）。
    ``top_pick_place_rate`` は、各レースで確率がいちばん高い馬の、目的変数が 1 だった割合。
    """

    timing: PredictionTiming
    model: str
    tree_count: int | None
    rows: int
    log_loss: float
    auc: float
    brier: float
    top_pick_place_rate: float
