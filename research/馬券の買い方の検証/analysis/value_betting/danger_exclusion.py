"""危険な人気馬（消）を決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.favorites_out_of_top3.danger import DangerThreshold
from yosou.favorites_out_of_top3.dataset import FavoriteBand

from . import columns as c


class DangerExclusion:
    """人気馬の危険度（4着以下の確率 − オッズから見た4着以下の確率）が、人気帯の線以上の人気馬を「消」にする
    （設計書 買うレースと買い目を決める 07 の 3）。

    線は人気帯（1番人気・2〜3番人気・4〜5番人気）ごとに、直前の1年の人気馬で決める（本番の ``DangerThreshold`` と同じ決め方。
    危険とした馬が同じ人気帯の全体より実際に4着以下になりやすいように）。線の決まらない人気帯は、消にしない。
    人気馬でない馬（人気馬モデルの確率が無い馬）は、危険度が欠損で、消にならない。
    """

    def __init__(self) -> None:
        self._lines: dict[str, float] = {}

    @property
    def lines(self) -> dict[str, float]:
        """人気帯 → 線（決まらなかった帯は無い）。"""
        return dict(self._lines)

    def fit(self, history: pd.DataFrame) -> DangerExclusion:
        """直前の1年の1頭ごとの行から、人気帯ごとの線を決める。"""
        rows = history.assign(**{c.DANGER: self._danger(history)}).dropna(subset=[c.DANGER])
        bands = FavoriteBand.labels_of(rows[c.POPULARITY])
        chooser = DangerThreshold()
        self._lines = {}
        for band in FavoriteBand:
            inside = rows[(bands == band.label).to_numpy()]
            line = chooser.choose(inside[c.DANGER], 1 - inside[c.TOP3].astype(float)) if len(inside) else float("nan")
            if not np.isnan(line):
                self._lines[band.label] = float(line)
        return self

    def mark(self, runners: pd.DataFrame) -> pd.DataFrame:
        """危険度（``danger``）と消（``excluded``）の列を足す。"""
        danger = self._danger(runners)
        line = FavoriteBand.labels_of(runners[c.POPULARITY]).map(self._lines).astype(float)
        excluded = (danger >= line.fillna(np.inf)).fillna(False)
        return runners.assign(**{c.DANGER: danger, c.EXCLUDED: excluded.to_numpy(dtype=bool)})

    def _danger(self, rows: pd.DataFrame) -> pd.Series:
        return rows[c.DANGER_PROB] - (1.0 - rows[c.MARKET_TOP3])
