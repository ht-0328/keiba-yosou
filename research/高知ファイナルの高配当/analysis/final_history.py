"""ファイナルレースの出走歴: 馬ごとに、今回より前のファイナルレースの出走数・3着以内の数・勝利数と、前走がファイナルだったか。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .final_race import FINAL

_HORSE = "horse_id"


@dataclass(frozen=True)
class FinalHistory:
    """``runs`` は馬ごとに古い順に並んだ高知の出走の行（``final``・``placed``・``won`` が付いたもの）。今回の出走は数えない。"""

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        out = runs.copy()
        in_final = runs[FINAL].astype(float)
        out["prev_run_final"] = in_final.groupby(runs[_HORSE]).shift(1).eq(1.0)
        out["final_runs_before"] = self._count_before(runs, in_final)
        out["final_places_before"] = self._count_before(runs, in_final * runs["placed"])
        out["final_wins_before"] = self._count_before(runs, in_final * runs["won"])
        return out

    def _count_before(self, runs: pd.DataFrame, flags: pd.Series) -> pd.Series:
        """今回より前の ``flags``（0 か 1）の合計。"""
        return flags.groupby(runs[_HORSE]).cumsum() - flags
