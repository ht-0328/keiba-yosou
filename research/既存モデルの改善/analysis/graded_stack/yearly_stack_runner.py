"""2段目を、テストの年ごとに、その年より前の重賞だけで学んで予測する。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .conditional_logit import ConditionalLogit
from .offset_logit import OffsetLogit
from .stack_features import StackFeatures
from .stack_table_builder import YEAR, Y_TOP3, Y_WIN

#: 罰の強さの候補。前の年で一番良かったものを使う（その年はまだ見ない）。
PENALTIES: tuple[float, ...] = (1.0, 10.0, 100.0, 1000.0)
#: 候補を比べる前の年が無いとき（学ぶ年が1年だけ）の罰。
DEFAULT_PENALTY = 100.0
_EPS = 1e-15


class YearlyStackRunner:
    """テストの年 Y ごとに、Y より前の年の重賞の行で2段目を学び、Y の重賞の行を予測する。

    罰の強さは、Y−1 年を除いた年で学んで Y−1 年のログ損失がいちばん小さい候補を選び、Y より前の年の全部で学び直す。
    3着以内は ``OffsetLogit``（出発点 = 1段目のロジット）、1着は ``ConditionalLogit``（出発点 = 1段目の1着の確率の対数）。
    戻り値は ``PredictionStore`` と同じ形の予測の表（3着以内と1着）と、年ごとに選んだ罰の記録。
    """

    def run(self, table: pd.DataFrame, years: Sequence[int]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        tops, wins, logs = [], [], []
        for year in years:
            train, test = table[table[YEAR] < year], table[table[YEAR] == year]
            if train.empty or test.empty:
                continue
            top3_penalty = self._penalty(train, "top3")
            win_penalty = self._penalty(train, "win")
            tops.append(self._frame(test, self._predict(train, test, "top3", top3_penalty), year))
            wins.append(self._frame(test, self._predict(train, test, "win", win_penalty), year))
            logs.append({"区切り": f"{year}年", "学習の行数": len(train), "3着以内の罰": top3_penalty, "1着の罰": win_penalty})
        return pd.concat(tops, ignore_index=True), pd.concat(wins, ignore_index=True), pd.DataFrame(logs)

    def _penalty(self, train: pd.DataFrame, target: str) -> float:
        last = train[YEAR].max()
        inner, check = train[train[YEAR] < last], train[train[YEAR] == last]
        if inner.empty:
            return DEFAULT_PENALTY
        losses = [self._loss(check, self._predict(inner, check, target, penalty), target) for penalty in PENALTIES]
        return PENALTIES[int(np.argmin(losses))]

    def _predict(self, train: pd.DataFrame, test: pd.DataFrame, target: str, penalty: float) -> np.ndarray:
        features = StackFeatures(target).fit(train)
        if target == "top3":
            model = OffsetLogit(penalty).fit(features.transform(train), features.offset(train), train[Y_TOP3].to_numpy())
            return model.predict(features.transform(test), features.offset(test))
        model = ConditionalLogit(penalty).fit(features.transform(train), features.offset(train), train[Y_WIN].to_numpy(), _groups(train))
        return model.predict(features.transform(test), features.offset(test), _groups(test))

    def _loss(self, rows: pd.DataFrame, probability: np.ndarray, target: str) -> float:
        label = rows[Y_TOP3 if target == "top3" else Y_WIN].to_numpy(dtype=float)
        clipped = np.clip(probability, _EPS, 1 - _EPS)
        return float(-np.mean(label * np.log(clipped) + (1 - label) * np.log(1 - clipped)))

    def _frame(self, test: pd.DataFrame, probability: np.ndarray, year: int) -> pd.DataFrame:
        return pd.DataFrame({"レースID": test["race_id"].to_numpy(), "開催日": test["race_date"].to_numpy(), "馬ID": test["horse_id"].to_numpy(),
                             "馬番": test["horse_no"].to_numpy(), "確率": probability, "区切り": f"{year}年", "期間": "テスト", "区分": "全体"})


def _groups(rows: pd.DataFrame) -> np.ndarray:
    """行ごとのレースの番号（0 から）。"""
    return pd.factorize(rows["race_id"])[0]
