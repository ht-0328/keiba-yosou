"""2段目の材料（1段目と市場のずれを直すのに使う、少数の数値の列）を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.stakes_tendency_top3.feature import K_FEATURES

from .stack_table_builder import BASE_TOP3, BASE_WIN, FIELD, MARKET_TOP3, MARKET_WIN

#: 0・1 から離す幅。
_EPS = 1e-6
#: 数を対数にする W の列。
_COUNTS = ("重賞の出走数", "重賞の3着以内の数", "重賞の勝利数", "G1の3着以内の数", "今回の格以上での3着以内の数", "同じ重賞の出走数", "同じ重賞の3着以内の数")
#: 欠損値なら「無い」の印を立てて 0 にする着順の列。
_FINISHES = ("直近の重賞の着順", "前年の同じ重賞の着順")
#: 0・1 の列にするカテゴリの値。
_CATEGORIES = {"格": ("G1", "G2"), "重量種別": ("ハンデ", "別定", "定量"), "前走の格": ("G1", "G2", "G3", "L", "OP", "前走なし")}
#: K の切り口（出走数・複勝率の組）。複勝率は出走数で縮める（出走が少ないと過去開催の平均に寄せる）。
_K_CUTS = tuple(feature.name.removeprefix("過去開催の").removesuffix("の出走数") for feature in K_FEATURES
                if feature.name.startswith("過去開催の") and feature.name.endswith("の出走数"))
_SHRINK = 10.0


def logit(values: pd.Series | np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=float), _EPS, 1 - _EPS)
    return np.log(clipped / (1 - clipped))


class StackFeatures:
    """2段目の材料の行列。目的変数ごとに、1段目と市場の確率の差（ロジット）、W、K（縮めた複勝率と過去開催の平均との差）、頭数。

    列の平均と散らばりは学習の行で決め（``fit``）、同じ値で予測の行もそろえる（``transform``）。
    出発点（1段目の確率）は材料に入れず、2段目のモデルの「ずらし」（offset）として渡す。
    """

    def __init__(self, target: str) -> None:
        self._base, self._market = (BASE_TOP3, MARKET_TOP3) if target == "top3" else (BASE_WIN, MARKET_WIN)
        self._mean: pd.Series | None = None
        self._scale: pd.Series | None = None

    def offset(self, frame: pd.DataFrame) -> np.ndarray:
        return logit(frame[self._base])

    def raw(self, frame: pd.DataFrame) -> pd.DataFrame:
        columns = {"1段目と市場の差": logit(frame[self._base]) - logit(frame[self._market]),
                   "市場のロジット": logit(frame[self._market]), "頭数（対数）": np.log(frame[FIELD].astype(float)),
                   "トップハンデとの差": frame["トップハンデとの差"].astype(float).fillna(0.0)}
        for name in _COUNTS:
            columns[name] = np.log1p(frame[name].astype(float).fillna(0.0))
        for name in _FINISHES:
            values = frame[name].astype(float)
            columns[f"{name}が無い"] = values.isna().astype(float)
            columns[name] = values.fillna(0.0)
        for name, values in _CATEGORIES.items():
            for value in values:
                columns[f"{name}={value}"] = (frame[name].astype(str) == value).astype(float)
        average = frame["過去開催の1〜3番人気の複勝率"].astype(float)
        base_rate = 0.2
        for cut in _K_CUTS:
            runs = frame[f"過去開催の{cut}の出走数"].astype(float).fillna(0.0)
            rate = frame[f"過去開催の{cut}の複勝率"].astype(float).fillna(base_rate)
            columns[f"K {cut}"] = (rate * runs + base_rate * _SHRINK) / (runs + _SHRINK) - base_rate
        columns["K 過去開催の数"] = np.log1p(frame["重賞の過去開催の数"].astype(float).fillna(0.0))
        columns["K 1〜3番人気の複勝率"] = average.fillna(0.6) - 0.6
        return pd.DataFrame(columns, index=frame.index)

    def fit(self, frame: pd.DataFrame) -> StackFeatures:
        raw = self.raw(frame)
        self._mean, self._scale = raw.mean(), raw.std().replace(0.0, 1.0).fillna(1.0)
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        if self._mean is None or self._scale is None:
            raise RuntimeError("fit を先に呼んでください")
        return ((self.raw(frame) - self._mean) / self._scale).fillna(0.0).to_numpy(dtype=float)
