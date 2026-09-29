"""各出走について、能力指数に使った近走に、今回と同じ条件の走が無いか（初めての条件か）を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ability_settings import FIRST_DISTANCE, FIRST_GOING, FIRST_SURFACE, FIRST_VENUE, AbilitySettings
from .past_runs import PastRuns

#: 距離帯の区切り（m）。1400m 以下・1401〜1800m・1801〜2200m・2201m 以上の4つ。
DISTANCE_EDGES: tuple[int, ...] = (1401, 1801, 2201)
DISTANCE_BANDS: tuple[str, ...] = ("〜1400m", "1401〜1800m", "1801〜2200m", "2201m〜")
#: 馬場状態（まだ発表されていないレースは、馬場の組を判定しない）。
_CONDITIONS: tuple[str, ...] = ("良", "稍重", "重", "不良")


def distance_band(distance: np.ndarray) -> np.ndarray:
    """距離（m）を、距離帯の番号（0〜3）にする。"""
    return np.digitize(np.asarray(distance, dtype=float), DISTANCE_EDGES)


class FirstConditions:
    """出走の表の各行に、近走（``runs`` 走・``window_days`` 以内。能力指数に使う走と同じ）に同じ条件の走が無いかの列を足す。

    足すのは ``pedigree_kinds`` の列だけ（True なら、その条件は初めて）。

    - 初めての距離帯: 同じ距離帯（``DISTANCE_BANDS``）の走が無い。例: 1600m と 1800m しか走っていない馬の 2400m。
    - 初めての競馬場: 同じ競馬場の走が無い。
    - 初めての芝ダ: 同じ芝ダの走が無い。例: 芝しか走っていない馬の、初めてのダート。
    - 初めての馬場の組: 同じ芝ダの走はあるが、その芝ダで同じ馬場の組（良・稍重 か、重・不良）の走が無い。
      初めての芝ダの行と、馬場状態がまだ発表されていない行は False。
    近走が1つも無い馬（新馬など。能力指数が付かない）は、どれも False。
    """

    def __init__(self, settings: AbilitySettings) -> None:
        self._settings = settings

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        past = PastRuns(runs, self._settings.runs, self._settings.window_days)
        used = np.isfinite(past.figure)
        has_any = used.any(axis=1)
        return runs.assign(**{kind: self._missing(kind, past, used, runs) & has_any for kind in self._settings.pedigree_kinds})

    def _missing(self, kind: str, past: PastRuns, used: np.ndarray, runs: pd.DataFrame) -> np.ndarray:
        if kind == FIRST_DISTANCE:
            band_now = distance_band(runs["distance_m"].to_numpy())
            return ~(used & (past.distance_band(DISTANCE_EDGES) == band_now[:, None])).any(axis=1)
        if kind == FIRST_VENUE:
            return ~(used & past.same("venue_code", runs["venue_code"])).any(axis=1)
        same_surface = used & past.same("surface", runs["surface"])
        if kind == FIRST_SURFACE:
            return ~same_surface.any(axis=1)
        same_going = (same_surface & past.same_going(runs["condition"])).any(axis=1)
        return same_surface.any(axis=1) & ~same_going & runs["condition"].isin(_CONDITIONS).to_numpy()
