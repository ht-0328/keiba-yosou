"""二値の予想の確率の誤差と見分けやすさ。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

#: 確率の端の丸め（ログ損失が無限大にならないように）。
_EDGE = 1e-9


class BinaryScores:
    """二値の予想（3着以内・4着以下）の当たり具合を出す。

    - ログ損失・Brier: 確率そのものの誤差。小さいほど良い（既存モデルの修正計画の 3 の「確率の誤差」）。
    - AUC: 目的変数が 1 の馬に、高い確率を付けられた割合。
    - 人気別 AUC: 同じ単勝人気の馬どうしで比べた AUC を、頭数で重み付けして平均したもの。0.5 なら、人気で
      説明できないところを何も当てていない（計画の 3 の「同じ人気の馬の見分けやすさ」）。
    """

    def of(self, label: pd.Series, probability: pd.Series, popularity: pd.Series) -> dict[str, float]:
        y = label.to_numpy(dtype=int)
        p = np.clip(probability.to_numpy(dtype="float64"), _EDGE, 1.0 - _EDGE)
        return {
            "頭数": int(len(y)),
            "ログ損失": float(log_loss(y, p, labels=[0, 1])),
            "Brier": float(brier_score_loss(y, p)),
            "AUC": self._auc(y, p),
            "人気別AUC": self._auc_within(y, p, popularity.to_numpy()),
            "確率の平均": float(p.mean()),
            "実際の割合": float(y.mean()),
        }

    def _auc(self, y: np.ndarray, p: np.ndarray) -> float:
        if y.min() == y.max():
            return float("nan")
        return float(roc_auc_score(y, p))

    def _auc_within(self, y: np.ndarray, p: np.ndarray, popularity: np.ndarray) -> float:
        frame = pd.DataFrame({"y": y, "p": p, "pop": popularity})
        pairs = [(len(group), self._auc(group["y"].to_numpy(), group["p"].to_numpy()))
                 for _, group in frame.groupby("pop") if group["y"].nunique() == 2]
        if not pairs:
            return float("nan")
        return float(np.average([auc for _, auc in pairs], weights=[count for count, _ in pairs]))
