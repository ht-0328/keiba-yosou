"""荒れ具合の4段階の確率と正解から、当たり具合を出す。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, log_loss, roc_auc_score

from yosou.shared.dataset import RACE_ID, TrainingData
from yosou.upset_level.dataset import BetType, UpsetLevel

#: 正解の列の名前と、券種の列の名前。
ACTUAL, BET = "正解", "券種"
_LEVELS = [level.value for level in UpsetLevel]
_LABELS = [level.label for level in UpsetLevel]


class UpsetScores:
    """荒れ具合の予測（1行 = 1レース × 1券種。固い〜超荒れの4つの確率）を、正解と突き合わせて当たり具合を出す。

    正解は、荒れ具合の学習データの目的変数（券種ごとの払戻から決めた段階）。出す値は
    正解率（いちばん高い段階が正解と一致した割合）・ログ損失（小さいほど良い）・マクロ F1・
    「中荒れ以上」の AUC（1 − 固いの確率で見分けられるか）・中荒れ以上の確率の平均と実際の割合。
    """

    def __init__(self, upset: TrainingData) -> None:
        frames = [pd.DataFrame({RACE_ID: upset.ids[RACE_ID].to_numpy(), BET: bet.label,
                                ACTUAL: upset.targets[bet.column_name].to_numpy()}) for bet in BetType]
        self._actual = pd.concat(frames, ignore_index=True).dropna(subset=[ACTUAL])

    def table(self, predictions: pd.DataFrame, by: Sequence[str]) -> pd.DataFrame:
        """``by`` の列（例: 方法・券種・区切り）ごとの当たり具合の表。正解の無い行は数えない。"""
        joined = predictions.merge(self._actual, on=[RACE_ID, BET], how="inner").dropna(subset=_LABELS)
        rows = [{**dict(zip(by, key if isinstance(key, tuple) else (key,))), **self._scores(group)}
                for key, group in joined.groupby(list(by), sort=False)]
        return pd.DataFrame(rows)

    def _scores(self, group: pd.DataFrame) -> dict[str, float]:
        probability = group[_LABELS].to_numpy(dtype="float64")
        probability = probability / probability.sum(axis=1, keepdims=True)
        actual = group[ACTUAL].to_numpy(dtype=int)
        top = probability.argmax(axis=1)
        upset = actual >= 1
        upset_probability = 1.0 - probability[:, 0]
        return {
            "レース数": len(group),
            "正解率": float((top == actual).mean()),
            "ログ損失": float(log_loss(actual, np.clip(probability, 1e-9, 1.0), labels=_LEVELS)),
            "マクロF1": float(f1_score(actual, top, labels=_LEVELS, average="macro", zero_division=0)),
            "中荒れ以上のAUC": float(roc_auc_score(upset, upset_probability)) if 0 < upset.sum() < len(upset) else np.nan,
            "中荒れ以上の確率の平均": float(upset_probability.mean()),
            "中荒れ以上の実際の割合": float(upset.mean()),
        }
