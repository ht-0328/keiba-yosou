"""レースのペースを、前半と後半の差で ハイ・ミドル・スロー に分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: ペースの区分。
SLOW, MIDDLE, HIGH = "スロー", "ミドル", "ハイ"
#: 出力の列。
PACE = "ペース"
#: ハイとスローを分ける z の線、基準に要るレースの数、標準偏差の下限（秒）。
_Z_LINE, _MIN_RACES, _MIN_STD = 0.5, 30, 0.1
_COURSE: tuple[str, ...] = ("venue_code", "track_code", "distance_m")
_WITH_CONDITION: tuple[str, ...] = (*_COURSE, "condition")


class PaceBalance:
    """前後半の差（前3ハロン − 後3ハロン、秒）を、同じ競馬場・コース・距離・馬場状態のレースの平均と比べて区分にする。

    研究「展開の理論の検証」で、脚質による有利・不利をいちばんはっきり分けた測り方
    （``research/展開の理論の検証/docs/02-結果の読み方.md``）。
    z =（基準の平均 − 前後半の差）÷ 基準の標準偏差。前半に偏って速いほどプラスで、0.5 より大きければハイ、
    −0.5 より小さければスロー。馬場状態ごとに 30 レースに満たなければ、馬場状態を分けない基準を使う。
    例: 基準の差が −0.5秒・標準偏差 0.8秒のコースで、前半 34.0・後半 36.0（差 −2.0秒）なら z = 1.9 でハイ。
    基準は ``fit`` に渡したレースだけから作る。
    """

    def __init__(self) -> None:
        self._by_condition = pd.DataFrame()
        self._by_course = pd.DataFrame()

    def fit(self, races: pd.DataFrame) -> PaceBalance:
        gap = self._gap(races)
        self._by_condition = self._stats(races, gap, _WITH_CONDITION)
        self._by_course = self._stats(races, gap, _COURSE)
        return self

    def band(self, races: pd.DataFrame) -> pd.Series:
        gap = self._gap(races)
        by_condition = self._lookup(races, self._by_condition, _WITH_CONDITION)
        by_course = self._lookup(races, self._by_course, _COURSE)
        stats = by_condition.where(by_condition["mean"].notna(), by_course)
        z = (stats["mean"] - gap) / stats["std"]
        labels = np.select([z > _Z_LINE, z < -_Z_LINE, z.notna()], [HIGH, SLOW, MIDDLE], default="")
        return pd.Series(labels, index=races.index).replace("", np.nan)

    def _gap(self, races: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(races["first3f"], errors="coerce") - pd.to_numeric(races["last3f_race"], errors="coerce")

    def _stats(self, races: pd.DataFrame, gap: pd.Series, keys: tuple[str, ...]) -> pd.DataFrame:
        stats = gap.groupby([races[key] for key in keys]).agg(["mean", "std", "count"])
        return stats[(stats["count"] >= _MIN_RACES) & (stats["std"] >= _MIN_STD)]

    def _lookup(self, races: pd.DataFrame, stats: pd.DataFrame, keys: tuple[str, ...]) -> pd.DataFrame:
        index = pd.MultiIndex.from_frame(races[list(keys)])
        return pd.DataFrame(stats[["mean", "std"]].reindex(index).to_numpy(), columns=["mean", "std"], index=races.index)
