"""同じ距離の出走歴: 馬ごと・距離ごとに、今回より前の高知の出走数と3着以内の数。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_KEYS = ["horse_id", "distance_m"]


@dataclass(frozen=True)
class DistanceHistory:
    """``runs`` は馬ごとに古い順に並んだ高知の出走の行（``placed`` が付いたもの）。今回の出走は数えない。"""

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        out = runs.copy()
        same_distance = runs.groupby(_KEYS)
        out["distance_runs_before"] = same_distance.cumcount()
        out["distance_places_before"] = same_distance["placed"].cumsum() - runs["placed"]
        return out
