"""ばんえいの2つのモデル: 勝つ確率の予想と、世間の買い方の見立て（確定の単勝の票の割合を、同じ材料から当てる）。"""

from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

#: 学習に使う最初の年（2016年は過去走の材料がそろわない）。
FIRST_TRAIN_YEAR = 2017
_PARAMS = {"learning_rate": 0.03, "num_leaves": 31, "min_data_in_leaf": 80, "feature_fraction": 0.6, "bagging_fraction": 0.8,
           "bagging_freq": 1, "lambda_l2": 5.0, "verbose": -1, "num_threads": 6, "seed": 2026}
_WIN_ROUNDS = 350
_CROWD_ROUNDS = 500
#: 票の割合の下限（対数にする前に切る）。
_MIN_SHARE = 1e-3
_WIN_FILE = "win.txt"
_CROWD_FILE = "crowd.txt"
_META_FILE = "meta.json"


class BaneiModel:
    def __init__(self, names: list[str], win: lgb.Booster, crowd: lgb.Booster) -> None:
        self._names = names
        self._win = win
        self._crowd = crowd

    @classmethod
    def fit(cls, features: pd.DataFrame, names: list[str]) -> BaneiModel:
        """確定した出走の特徴量から学ぶ。世間の見立ては、確定オッズのある出走だけで学ぶ。"""
        train = features[features["date"].dt.year >= FIRST_TRAIN_YEAR]
        win = lgb.train(_PARAMS | {"objective": "binary"}, lgb.Dataset(train[names], train["win"]), num_boost_round=_WIN_ROUNDS)
        share = 1 / train["win_odds"].where(train["win_odds"] > 0)
        share = share / share.groupby(train["rid"]).transform("sum")
        known = share.notna()
        target = np.log(share[known].clip(lower=_MIN_SHARE))
        crowd = lgb.train(_PARAMS | {"objective": "regression"}, lgb.Dataset(train.loc[known, names], target), num_boost_round=_CROWD_ROUNDS)
        return cls(names, win, crowd)

    @classmethod
    def load(cls, folder: Path) -> BaneiModel:
        meta = json.loads((folder / _META_FILE).read_text(encoding="utf-8"))
        return cls(meta["names"], cls._read(folder / _WIN_FILE), cls._read(folder / _CROWD_FILE))

    def save(self, folder: Path, trained_until: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / _WIN_FILE).write_text(self._win.model_to_string(), encoding="utf-8")
        (folder / _CROWD_FILE).write_text(self._crowd.model_to_string(), encoding="utf-8")
        meta = {"names": self._names, "trained_until": trained_until}
        (folder / _META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    @staticmethod
    def _read(path: Path) -> lgb.Booster:
        """LightGBM は日本語の入ったパスを自分では読み書きできないので、文字列で受け渡す。"""
        return lgb.Booster(model_str=path.read_text(encoding="utf-8"))

    def predict(self, race: pd.DataFrame) -> pd.DataFrame:
        """1レースの出走馬に、勝つ確率 ``p_win`` と世間の見立て ``c_win`` を足す（どちらもレースの中で合計 1）。"""
        out = race.copy()
        win = self._win.predict(out[self._names])
        crowd = np.exp(self._crowd.predict(out[self._names]))
        out["p_win"] = win / win.sum()
        out["c_win"] = crowd / crowd.sum()
        return out
