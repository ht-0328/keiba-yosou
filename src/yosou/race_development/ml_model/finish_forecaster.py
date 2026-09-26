"""⑦ の1着の確率から、各馬の 1着・2着以内・3着以内の確率を出す。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_ID
from yosou.shared.ml_model import EnsembleModel, FeatureData

from .order_probability import OrderProbability

#: λ を書くファイルの名前（⑦ のモデルと同じフォルダ。設計書 12 の 6）。
LAMBDA_FILE = "order_lambda.json"
#: 出力の列。
WIN, TOP2, TOP3 = "1着の確率", "2着以内の確率", "3着以内の確率"


class FinishForecaster:
    """⑦ のアンサンブル（``EnsembleModel``）と λ を持ち、1レースの各馬の 1着・2着以内・3着以内の確率を出す（設計書 04 の「ml_model/」）。

    1着の確率は、LightGBM と CatBoost の、レースの中で合計 1 にそろえた確率の平均（合計 1 どうしの平均なので合計 1）。
    2着以内・3着以内は、そこから Harville の式（ならしの指数 λ 付き）で出す。
    """

    def __init__(self, ensemble: EnsembleModel, lam: float) -> None:
        self._ensemble = ensemble
        self._lambda = lam
        self._order = OrderProbability()

    @property
    def order_lambda(self) -> float:
        return self._lambda

    def win_probability(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの1着の確率（同じレースを足すと 1）。"""
        return self._ensemble.predict_proba(data)

    def forecast(self, data: FeatureData) -> pd.DataFrame:
        """列は ``1着の確率``・``2着以内の確率``・``3着以内の確率``。行の並びと index は ``data.features`` と同じ。"""
        win = self.win_probability(data)
        places = np.full((len(win), 3), np.nan)
        for rows in pd.Series(np.arange(len(win))).groupby(data.ids[RACE_ID].to_numpy()).indices.values():
            places[rows] = self._order.places(win[rows], self._lambda)
        return pd.DataFrame(places, columns=[WIN, TOP2, TOP3], index=data.features.index)

    def save_lambda(self, folder: Path) -> None:
        (Path(folder) / LAMBDA_FILE).write_text(json.dumps({"order_lambda": self._lambda}) + "\n", encoding="utf-8")

    @staticmethod
    def load_lambda(folder: Path) -> float:
        return float(json.loads((Path(folder) / LAMBDA_FILE).read_text(encoding="utf-8"))["order_lambda"])
