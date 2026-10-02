"""1つの区切りで LightGBM を学習し、テストの行の3着以内の確率を出す。"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from .window_split import WindowSplit

#: ハイパーパラメータの初期値（今の予想の初期値と同じ。木の数の上限だけ多め）。
DEFAULT_PARAMS: dict[str, object] = {
    "learning_rate": 0.05, "n_estimators": 3000, "num_leaves": 31, "min_child_samples": 100, "subsample": 0.8,
    "subsample_freq": 1, "colsample_bytree": 0.8, "random_state": 42, "verbose": -1,
}
#: 検証データで、木を何本足しても良くならなければ止めるか。
EARLY_STOPPING_ROUNDS = 100


class LightGBMWindowModel:
    """二値分類（3着以内か）。``params`` は初期値に上書きする値（例: 木を小さくするなら num_leaves）。"""

    name = "LightGBM"

    def __init__(self, params: dict[str, object] | None = None) -> None:
        self._params = {**DEFAULT_PARAMS, **(params or {})}

    def fit(self, frame: pd.DataFrame, columns: list[str], split: WindowSplit) -> lgb.LGBMClassifier:
        """学習の行で学び、検証の行で木の数を決めたモデル。"""
        train, valid = split.train(frame), split.valid(frame)
        model = lgb.LGBMClassifier(**self._params)
        model.fit(train[columns], train["3着以内"], eval_set=[(valid[columns], valid["3着以内"])],
                  callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)])
        return model

    def predict(self, frame: pd.DataFrame, columns: list[str], split: WindowSplit) -> tuple[np.ndarray, int]:
        """（テストの行の確率, 木の数）。"""
        model = self.fit(frame, columns, split)
        return model.predict_proba(split.test(frame)[columns])[:, 1], int(model.best_iteration_)
