"""目的変数に対する確率の当たり具合。"""

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.ml_model import EnsembleModel


class ProbabilityScores:
    """件数・正例率・ログ損失・Brier・AUC を、モデルごと（平均と2つのモデル）と、平均の人気ごとに出す。"""

    def evaluate(self, ensemble: EnsembleModel, data: TrainingData) -> list[dict]:
        if len(data) == 0:
            return [{"モデル": "平均", "人気": "全体", **self.scores(data.label, np.array([]))}]
        probabilities = ensemble.predict_members(data)
        probabilities["平均"] = ensemble.combine(probabilities)
        rows = [{"モデル": name, "人気": "全体", **self.scores(data.label, probability)}
                for name, probability in probabilities.items()]
        popularity = data.evaluation[POPULARITY]
        for rank in sorted(popularity.dropna().unique()):
            mask = popularity.eq(rank).fillna(False)
            rows.append({"モデル": "平均", "人気": str(int(rank)),
                         **self.scores(data.label[mask], probabilities["平均"][mask.to_numpy(dtype=bool)])})
        if popularity.isna().any():
            mask = popularity.isna()
            rows.append({"モデル": "平均", "人気": "不明", **self.scores(data.label[mask], probabilities["平均"][mask.to_numpy()])})
        return rows

    def scores(self, labels: pd.Series, probability: np.ndarray) -> dict:
        if len(labels) == 0:
            return {"件数": 0, "正例率": None, "ログ損失": None, "Brier": None, "AUC": None, "注記": "対象なし"}
        both = labels.nunique() == 2
        return {
            "件数": len(labels), "正例率": float(labels.mean()),
            "ログ損失": float(log_loss(labels, probability, labels=[0, 1])),
            "Brier": float(brier_score_loss(labels, probability)),
            "AUC": float(roc_auc_score(labels, probability)) if both else None,
            "注記": "" if both else "正解が1クラスのみのためAUCは計算不能",
        }
