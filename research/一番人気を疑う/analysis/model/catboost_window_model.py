"""1つの区切りで CatBoost を学習し、テストの行の3着以内の確率を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from .window_split import WindowSplit

#: ハイパーパラメータ（今の予想の初期値に近い。学習の速さのため、学習率だけ少し上げている）。
DEFAULT_PARAMS: dict[str, object] = {
    "iterations": 3000, "learning_rate": 0.08, "depth": 6, "l2_leaf_reg": 3, "random_seed": 42, "verbose": 0,
    "early_stopping_rounds": 100,
}


class CatBoostWindowModel:
    """二値分類（3着以内か）。カテゴリの材料は、CatBoost に文字列のまま渡す。"""

    name = "CatBoost"

    def __init__(self, params: dict[str, object] | None = None) -> None:
        self._params = {**DEFAULT_PARAMS, **(params or {})}

    def predict(self, frame: pd.DataFrame, columns: list[str], split: WindowSplit) -> tuple[np.ndarray, int]:
        """（テストの行の確率, 木の数）。"""
        categories = [column for column in columns if isinstance(frame[column].dtype, pd.CategoricalDtype)]
        train, valid, test = (self._plain(rows, columns, categories) for rows in
                              (split.train(frame), split.valid(frame), split.test(frame)))
        model = CatBoostClassifier(**self._params)
        model.fit(train[0], train[1], cat_features=categories, eval_set=(valid[0], valid[1]))
        return model.predict_proba(test[0])[:, 1], int(model.get_best_iteration())

    @staticmethod
    def _plain(rows: pd.DataFrame, columns: list[str], categories: list[str]) -> tuple[pd.DataFrame, pd.Series]:
        values = rows[columns].assign(**{column: rows[column].astype(str) for column in categories})
        return values, rows["3着以内"]
