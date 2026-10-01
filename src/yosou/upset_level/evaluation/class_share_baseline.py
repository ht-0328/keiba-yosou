"""モデルによらない2つの基準（常に最多クラス・クラスの割合をそのまま確率にする）を測る。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import numpy as np

from yosou.shared.dataset import SplitData, TrainingData
from yosou.shared.evaluation import ClassEvaluation, ClassMetricCalculator
from yosou.shared.feature import PredictionTiming

#: 基準の名前（``ClassEvaluation.model`` に入れる）。
MOST_FREQUENT = "常に最多クラス"
CLASS_SHARES = "クラスの割合をそのまま確率にする"


class ClassShareBaseline:
    """学習データの4クラスの割合だけから作る、モデルによらない2つの基準の当たり具合を、検証データで測る（設計書 16 の 3）。

    - 常に最多クラス: 学習データでいちばん多いクラスを、全レースに出す（そのクラスの確率を 1、ほかを 0 とみなす）。
      正解率の下限。確率として使うものではないので、ログ損失と AUC は出さない（NaN）。
    - クラスの割合をそのまま確率にする: 学習データの4クラスの割合を、全レースに同じ確率として出す。ログ損失の下限。
      どのレースも同じ確率なので、AUC は 0.5 になる。

    特徴量を使わないので、値は時点によらない。この予想の時点ごとの行と並べるため、時点ごとに同じ値を返す。
    """

    def evaluate(self, split: SplitData, timings: Sequence[PredictionTiming]) -> list[ClassEvaluation]:
        """時点ごとに、常に最多クラス・クラスの割合の順の行。"""
        shares = self._shares(split.train)
        valid = split.valid
        calculator = ClassMetricCalculator(valid)
        most_frequent = np.tile(np.eye(len(shares))[shares.argmax()], (len(valid), 1))
        class_shares = np.tile(shares, (len(valid), 1))
        uppers = valid.class_labels[1:]
        first = timings[0]
        baselines = (
            ClassEvaluation(
                first, MOST_FREQUENT, None, len(valid), calculator.accuracy(most_frequent),
                calculator.macro_f1(most_frequent), calculator.mean_class_gap(most_frequent),
                float("nan"), (float("nan"),) * len(uppers), calculator.confusion_matrix(most_frequent),
            ),
            ClassEvaluation(
                first, CLASS_SHARES, None, len(valid), calculator.accuracy(class_shares),
                calculator.macro_f1(class_shares), calculator.mean_class_gap(class_shares),
                calculator.log_loss(class_shares),
                tuple(calculator.cumulative_auc(class_shares, label) for label in uppers),
                calculator.confusion_matrix(class_shares),
            ),
        )
        return [replace(baseline, timing=timing) for timing in timings for baseline in baselines]

    def _shares(self, train: TrainingData) -> np.ndarray:
        """学習データの、クラスの番号の順の割合（出てこないクラスは 0）。"""
        counts = train.label.astype(int).value_counts()
        values = np.array([counts.get(label, 0) for label in train.class_labels], dtype=float)
        return values / values.sum()
