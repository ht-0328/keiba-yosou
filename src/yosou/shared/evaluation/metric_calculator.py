"""予測確率と正解から、評価指標を計算する。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from ..dataset import RACE_ID, TrainingData
from ..dataset.column_names import PLACE_PAYOUT, POPULARITY
from ..feature import as_numbers

#: 目的変数の値（0 と 1）。
_LABELS = [0, 1]
#: 複勝の払戻は 100円あたりの円。回収率は、払戻の合計 ÷（100円 × 買った頭数）。
_STAKE = 100.0


class MetricCalculator:
    """1つのデータ（学習に使っていないもの）について、予測確率の当たり具合を計算する（穴馬の設計書 16）。

    一般的な指標（ログ損失・AUC・Brier）のほかに、「人気順をなぞるだけになっていないか」を見るために、
    各レースで確率がいちばん高い馬と、人気がいちばん上の馬（基準）を同じ物差しで比べる。
    """

    def __init__(self, data: TrainingData) -> None:
        self._label = data.label.to_numpy()
        self._race_ids = data.ids[RACE_ID].to_numpy()
        self._popularity = as_numbers(data.evaluation[POPULARITY]).to_numpy()
        self._place_payout = as_numbers(data.evaluation[PLACE_PAYOUT]).fillna(0.0).to_numpy()

    def log_loss(self, probability: np.ndarray) -> float:
        """ログ損失。確率が正解から外れるほど大きい。"""
        return float(log_loss(self._label, probability, labels=_LABELS))

    def auc(self, probability: np.ndarray) -> float:
        """AUC。目的変数が 1 の馬に、そうでない馬より高い確率を付けられた割合。正解が片方しか無ければ NaN。"""
        return self._auc_of(self._label, probability)

    def brier(self, probability: np.ndarray) -> float:
        """Brier スコア。確率と正解（0 か 1）の差の2乗の平均。"""
        return float(brier_score_loss(self._label, probability))

    def top_pick_place_rate(self, probability: np.ndarray) -> float:
        """各レースで確率がいちばん高い馬の、目的変数が 1 だった割合。"""
        return float(self._label[self._top_pick_rows(probability)].mean())

    def top_pick_place_payback(self, probability: np.ndarray) -> float:
        """各レースで確率がいちばん高い馬の複勝を 100円ずつ買ったときの回収率（払戻の合計 ÷ 買った金額）。"""
        return self._payback(self._top_pick_rows(probability))

    def popularity_pick_place_rate(self) -> float:
        """各レースで確定単勝人気がいちばん上の馬の、目的変数が 1 だった割合（人気の基準。モデルによらない）。"""
        return float(self._label[self._popularity_pick_rows()].mean())

    def popularity_pick_place_payback(self) -> float:
        """各レースで確定単勝人気がいちばん上の馬の複勝を 100円ずつ買ったときの回収率（人気の基準）。"""
        return self._payback(self._popularity_pick_rows())

    def auc_within_popularity(self, probability: np.ndarray) -> float:
        """同じ確定単勝人気の馬どうしで比べた AUC（人気で説明できない部分を、どれだけ当てているか）。

        人気ごとに AUC を出し、頭数で重み付けして平均する。正解が片方しか無い人気は数えない。
        どの人気も数えられなければ NaN。0.5 なら、人気で説明できないところを何も当てていない。
        """
        runners = pd.DataFrame({
            "popularity": self._popularity, "probability": probability, "label": self._label,
        })
        groups = [group for _, group in runners.groupby("popularity", sort=False) if group["label"].nunique() == 2]
        if not groups:
            return float("nan")
        aucs = [self._auc_of(group["label"].to_numpy(), group["probability"].to_numpy()) for group in groups]
        return float(np.average(aucs, weights=[len(group) for group in groups]))

    def _auc_of(self, label: np.ndarray, probability: np.ndarray) -> float:
        has_both_labels = len(np.unique(label)) == len(_LABELS)
        if not has_both_labels:
            return float("nan")
        return float(roc_auc_score(label, probability))

    def _top_pick_rows(self, probability: np.ndarray) -> np.ndarray:
        """各レースで確率がいちばん高い馬の行の位置。"""
        runners = pd.DataFrame({"race": self._race_ids, "value": probability})
        return runners.groupby("race", sort=False)["value"].idxmax().to_numpy()

    def _popularity_pick_rows(self) -> np.ndarray:
        """各レースで人気がいちばん上（人気の値がいちばん小さい）の馬の行の位置。人気の無い馬は選ばない。"""
        popularity = np.where(np.isnan(self._popularity), np.inf, self._popularity)
        runners = pd.DataFrame({"race": self._race_ids, "value": popularity})
        return runners.groupby("race", sort=False)["value"].idxmin().to_numpy()

    def _payback(self, rows: np.ndarray) -> float:
        return float(self._place_payout[rows].sum() / (_STAKE * len(rows)))
