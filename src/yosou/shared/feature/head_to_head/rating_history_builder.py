"""出走の記録を開催日の順にたどって、出走ごとの「そのレースの前日までのレーティング」を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .elo_race_update import EloRaceUpdate
from .head_to_head_columns import (
    INITIAL_RATING,
    K_FACTOR,
    K_FACTOR_NEW,
    NEW_HORSE_RUNS,
    RATING,
    RUN_COUNT,
)


class RatingHistoryBuilder:
    """全出走（``runs``。``HeadToHeadRunRepository`` が読んだもの）から、出走ごとのレーティングの履歴を作る。

    開催日ごとに「その日の出走の行に、その時点のレーティングを書く → その日のレースの着順でレーティングを更新する」を
    くり返す。書くのが先なので、どの行のレーティングも、その開催日より前のレースの結果だけでできている
    （同じ日の先に終わったレースも使わない。設計書 11 の 2）。まだ走っていないレース（着順が欠損値）は、書くだけで更新しない。
    着順の付かなかった馬（競走中止など）は、そのレースの勝ち負けに数えない。

    列は ``race_id``・``horse_id``・``race_date``・``対戦レーティング``・``対戦レーティングの対戦数``（それまでに勝ち負けを
    数えたレースの数）。行の並びと index は ``runs`` と同じ。
    """

    def __init__(self) -> None:
        self._update = EloRaceUpdate()

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        ordered = runs.sort_values(["race_date", "race_id"], kind="stable")
        horse_codes, horses = pd.factorize(ordered["horse_id"].astype(str))
        finishes = pd.to_numeric(ordered["finish"], errors="coerce").to_numpy(dtype=float)
        ratings = np.full(len(horses), INITIAL_RATING)
        counts = np.zeros(len(horses), dtype=int)
        # レースID の列は1度だけ配列にする（開催日ごとに列全体を変換し直すと、それだけで1分以上かかる）
        race_ids = ordered["race_id"].to_numpy()
        before = np.empty(len(ordered))
        runs_before = np.empty(len(ordered), dtype=int)
        for start, end in _slices(ordered["race_date"].to_numpy()):
            codes = horse_codes[start:end]
            before[start:end] = ratings[codes]
            runs_before[start:end] = counts[codes]
            self._update_day(race_ids[start:end], start, horse_codes, finishes, ratings, counts)
        history = pd.DataFrame({
            "race_id": ordered["race_id"].to_numpy(), "horse_id": ordered["horse_id"].to_numpy(),
            "race_date": ordered["race_date"].to_numpy(), RATING: before, RUN_COUNT: runs_before.astype(float),
        }, index=ordered.index)
        return history.loc[runs.index]

    def _update_day(self, race_ids: np.ndarray, start: int, horse_codes: np.ndarray,
                    finishes: np.ndarray, ratings: np.ndarray, counts: np.ndarray) -> None:
        """1つの開催日のレースを順に、着順でレーティングを更新する。``race_ids`` はその日の行のレースID、``start`` はその日の最初の行。"""
        for race_start, race_end in _slices(race_ids):
            rows = np.arange(start + race_start, start + race_end)
            finished = rows[np.isfinite(finishes[rows])]
            self._update_race(horse_codes[finished], finishes[finished], ratings, counts)

    def _update_race(self, codes: np.ndarray, finishes: np.ndarray, ratings: np.ndarray, counts: np.ndarray) -> None:
        """1レースの着順で更新する。勝ち負けを数えられるのは、着順の付いた馬が2頭以上のとき。"""
        if len(codes) < 2:
            return
        k_factors = np.where(counts[codes] < NEW_HORSE_RUNS, K_FACTOR_NEW, K_FACTOR)
        ratings[codes] += self._update.deltas(ratings[codes], finishes, k_factors)
        counts[codes] += 1


def _slices(values: np.ndarray) -> list[tuple[int, int]]:
    """同じ値が続く区間の（始まり, 終わりの次）。``values`` は同じ値がまとまって並んでいること。"""
    if len(values) == 0:
        return []
    changes = np.flatnonzero(values[1:] != values[:-1]) + 1
    starts = np.concatenate([[0], changes])
    ends = np.concatenate([changes, [len(values)]])
    return list(zip(starts.tolist(), ends.tolist()))
