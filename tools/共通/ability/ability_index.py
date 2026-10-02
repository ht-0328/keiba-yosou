"""出走ごとの能力指数（近走のスピード指数を、新しさと今回の条件への近さで重み付けした平均）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ability_settings import COURSE, DISTANCE, GOING, AbilitySettings
from .past_runs import PastRuns

#: 出力の列。
ABILITY, BASE, RUNS_USED = "能力指数", "基礎の速さ", "使った走の数"
APTITUDE_COLUMNS = {DISTANCE: "距離の適性", COURSE: "コースの適性", GOING: "馬場の適性"}


class AbilityIndex:
    """スピード指数の付いた出走の表の各行に、その走より前の走だけから作った能力指数を足す。

    近 ``runs`` 走（``window_days`` 以内）のスピード指数の重み付き平均。重み = 新しさ × 今回の条件への近さ。

    - 基礎の速さ: 新しさだけで重みを付けた平均（条件を問わない、その馬のいまの力）。
    - 距離・コース・馬場の適性: その条件の近さだけを重みに足した平均 − 基礎の速さ。馬場は芝ダと馬場の組の両方。
      例: 1600m で速く 2400m で遅い馬が 1600m に出るなら、1600m に近い走が重くなり、距離の適性はプラスになる。
    - 能力指数: ``aptitudes`` の条件の近さを全部重みに入れた平均。適性の3つを足した値とは、ほぼ同じだが一致はしない。
    使える走が無い馬（新馬など）は欠損値。今回の走の結果は使わないので、これから走るレースの行にも付く。
    """

    def __init__(self, settings: AbilitySettings) -> None:
        self._settings = settings

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        s = self._settings
        past = PastRuns(runs, s.runs, s.window_days)
        recency = s.recency ** np.arange(s.runs)[None, :]
        nearness = {
            DISTANCE: np.exp(-past.distance_gap(runs["distance_m"]) / s.distance_scale),
            COURSE: np.where(past.same("venue_code", runs["venue_code"]), 1.0, s.other_venue),
            GOING: (np.where(past.same("surface", runs["surface"]), 1.0, s.other_surface)
                    * np.where(past.same_going(runs["condition"]), 1.0, s.other_going)),
        }
        base = self._weighted(past.figure, recency)
        aptitudes = {APTITUDE_COLUMNS[name]: self._weighted(past.figure, recency * nearness[name]) - base
                     for name in nearness}
        all_nearness = np.prod([nearness[name] for name in s.aptitudes], axis=0) if s.aptitudes else 1.0
        ability = self._weighted(past.figure, recency * all_nearness)
        return runs.assign(**{BASE: base, **aptitudes, ABILITY: ability,
                              RUNS_USED: np.isfinite(past.figure).sum(axis=1)})

    def _weighted(self, figures: np.ndarray, weights: np.ndarray) -> np.ndarray:
        used = np.where(np.isfinite(figures), weights, 0.0)
        total = used.sum(axis=1)
        summed = (np.nan_to_num(figures) * used).sum(axis=1)
        return np.where(total > 0, summed / np.where(total > 0, total, 1.0), np.nan)
