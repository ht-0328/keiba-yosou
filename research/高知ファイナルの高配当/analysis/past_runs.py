"""近走の材料: 馬ごとに、今回より前の高知の出走だけから、位置・着差・着順・人気・上がりの近走の値を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_HORSE = "horse_id"
#: 近走として見る走数。
_SHORT, _LONG = 3, 5
#: 1つ前の出走（高知）からそのまま持ってくる列 → 付ける列の名前。
_PREVIOUS: dict[str, str] = {
    "last3f_rank": "prev_run_last3f_rank", "distance_m": "prev_run_distance_m",
    "class_order": "prev_run_class_order", "carried": "prev_run_carried",
}


@dataclass(frozen=True)
class PastRuns:
    """``runs`` は馬ごとに古い順に並んだ高知の出走の行（``corner4_rel``・``corner1_rel``・``placed`` が付いたもの）。

    どの列も今回の出走を含めない（1つずらしてから数える）。高知での出走が無い馬は欠損値になる。
    """

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        out = runs.copy()
        out["corner4_rel_recent3"] = self._recent(runs, "corner4_rel", _SHORT, "mean")
        out["corner1_rel_recent3"] = self._recent(runs, "corner1_rel", _SHORT, "mean")
        out["time_diff_recent3"] = self._recent(runs, "time_diff", _SHORT, "mean")
        out["popularity_recent3"] = self._recent(runs, "popularity", _SHORT, "mean")
        out["places_recent5"] = self._recent(runs, "placed", _LONG, "sum")
        out["time_diff_best5"] = self._recent(runs, "time_diff", _LONG, "min")
        out["last3f_rank_recent5"] = self._recent(runs, "last3f_rank", _LONG, "mean")
        for source, name in _PREVIOUS.items():
            out[name] = runs.groupby(_HORSE)[source].shift(1)
        return out

    def _recent(self, runs: pd.DataFrame, column: str, count: int, how: str) -> pd.Series:
        """今回より前の ``count`` 走の ``how``（mean・sum・min）。値のある走が1つでもあれば数える。"""
        before = runs.groupby(_HORSE)[column].shift(1)
        windows = before.groupby(runs[_HORSE]).rolling(count, min_periods=1)
        return getattr(windows, how)().reset_index(level=0, drop=True)
