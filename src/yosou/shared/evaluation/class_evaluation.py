"""1つの時点・1つのモデルの、多クラス分類の当たり具合。"""

from __future__ import annotations

from dataclasses import dataclass

from ..feature import PredictionTiming


@dataclass(frozen=True)
class ClassEvaluation:
    """多クラス分類の当たり具合の値（荒れ具合の設計書 16 の 2）。

    正解率・マクロ F1・累積確率の AUC は大きいほど、クラスのずれの平均・ログ損失は小さいほど良い。
    ``tree_count`` は早期終了で残った木の数（アンサンブルの行では None）。
    ``cumulative_auc`` は「クラス 1 以上」「クラス 2 以上」… の順（クラスの数 − 1 個）。
    ``confusion_matrix`` は、行が実際のクラス、列がいちばん高いクラス。
    """

    timing: PredictionTiming
    model: str
    tree_count: int | None
    rows: int
    accuracy: float
    macro_f1: float
    mean_class_gap: float
    log_loss: float
    cumulative_auc: tuple[float, ...]
    confusion_matrix: tuple[tuple[int, ...], ...]
