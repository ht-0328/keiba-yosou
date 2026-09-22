"""1つの時点・1つのモデルの当たり具合。"""

from __future__ import annotations

from dataclasses import dataclass

from ..feature import PredictionTiming


@dataclass(frozen=True)
class Evaluation:
    """当たり具合の値（穴馬の設計書 16）。ログ損失と Brier は小さいほど、AUC と割合・回収率は大きいほど良い。

    - ``tree_count``: 早期終了で残った木の数（アンサンブルの行では None）。
    - ``top_pick_place_rate``・``top_pick_place_payback``: 各レースで確率がいちばん高い馬の、目的変数が 1 だった割合と、
      複勝の回収率。
    - ``popularity_pick_place_rate``・``popularity_pick_place_payback``: 各レースで確定単勝人気がいちばん上の馬の同じ値
      （人気の基準。モデルによらないので、同じ時点の行はどれも同じ値）。
    - ``auc_within_popularity``: 同じ人気の馬どうしで比べた AUC。0.5 なら、人気で説明できないところを何も当てていない。
    """

    timing: PredictionTiming
    model: str
    tree_count: int | None
    rows: int
    log_loss: float
    auc: float
    brier: float
    top_pick_place_rate: float
    top_pick_place_payback: float
    popularity_pick_place_rate: float
    popularity_pick_place_payback: float
    auc_within_popularity: float
