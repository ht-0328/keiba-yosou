"""「裏が当たるか」を当てるモデル（LightGBM と CatBoost の確率の平均）を、学ぶ・ファイルに書く・読む・予測する。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Self

import joblib
import lightgbm
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from 今週の予想.reverse_exacta_features import FEATURES

#: 置き場所の中のファイル名。
LIGHTGBM_FILE = "lightgbm.joblib"
CATBOOST_FILE = "catboost.cbm"
MANIFEST_FILE = "model.json"
#: 学び方（研究「裏目を買うかの予想」で確かめたもの。木の数は固定で、早期終了はしない）。
_LIGHTGBM_PARAMS = {"n_estimators": 400, "learning_rate": 0.02, "num_leaves": 15, "min_child_samples": 100, "subsample": 0.8,
                    "subsample_freq": 1, "colsample_bytree": 0.8, "reg_lambda": 5.0, "verbose": -1}
_CATBOOST_PARAMS = {"iterations": 600, "learning_rate": 0.03, "depth": 4, "l2_leaf_reg": 10, "verbose": 0}


class ReverseExactaModel:
    """材料（``ReverseExactaFeatures`` の ``FEATURES``。1行 = 1レース）から、そのレースで裏（1着が ○▲☆ のどれかで、◎ が2着か3着）が
    当たる確率を出す。LightGBM と CatBoost で学び、2つの確率の平均を返す。``threads`` は学ぶときに使うスレッドの数。

    モデルは JV-Data から学んだもので公開しないので、置き場所は Git の対象外の ``reports/`` の下にする。
    """

    def __init__(self, lightgbm_model: lightgbm.LGBMClassifier, catboost_model: CatBoostClassifier) -> None:
        self._lightgbm = lightgbm_model
        self._catboost = catboost_model

    @classmethod
    def fit(cls, features: pd.DataFrame, labels: pd.Series, threads: int = 4) -> Self:
        table = features[list(FEATURES)]
        first = lightgbm.LGBMClassifier(**_LIGHTGBM_PARAMS, n_jobs=threads).fit(table, labels)
        second = CatBoostClassifier(**_CATBOOST_PARAMS, thread_count=threads).fit(table, labels)
        return cls(first, second)

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """1行ずつの、裏が当たる確率。"""
        table = features[list(FEATURES)]
        return (self._lightgbm.predict_proba(table)[:, 1] + self._catboost.predict_proba(table)[:, 1]) / 2

    def save(self, folder: Path, counts: dict[str, int]) -> Path:
        """``folder`` に2つのモデルと、材料の並び・学んだ件数（``counts``）を書く。前のものは置き換える。"""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._lightgbm, folder / LIGHTGBM_FILE)
        self._catboost.save_model(str(folder / CATBOOST_FILE))
        manifest = {"features": list(FEATURES), "counts": counts}
        (folder / MANIFEST_FILE).write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return folder

    @classmethod
    def load(cls, folder: Path) -> Self | None:
        """``save`` で書いたモデル。無いか、材料の並びが今と違えば None（裏を買わない）。"""
        folder = Path(folder)
        if not all((folder / name).is_file() for name in (LIGHTGBM_FILE, CATBOOST_FILE, MANIFEST_FILE)):
            return None
        manifest = json.loads((folder / MANIFEST_FILE).read_text(encoding="utf-8"))
        if tuple(manifest.get("features", ())) != FEATURES:
            return None
        second = CatBoostClassifier()
        second.load_model(str(folder / CATBOOST_FILE))
        return cls(joblib.load(folder / LIGHTGBM_FILE), second)
