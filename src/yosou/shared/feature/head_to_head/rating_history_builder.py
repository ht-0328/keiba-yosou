"""出走の記録を開催日の順にたどって、出走ごとの「材料の締めの日の時点のレーティング」を作る。"""

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

#: 材料の締めの日の列（対象の行だけ。無ければ、開催日の前日の時点のレーティングを書く）。
_AS_OF_DATE = "as_of_date"
_ONE_DAY = np.timedelta64(1, "D")
#: 日ごとの手順の種類（並べ替えの順。同じ日なら、書いてから更新する）。
_WRITE, _UPDATE = 0, 1


class RatingHistoryBuilder:
    """全出走（``runs``。``HeadToHeadRunRepository`` が読んだもの）から、出走ごとのレーティングの履歴を作る。

    開催日ごとに「その日に書く行に、その時点のレーティングを書く → その日のレースの着順でレーティングを更新する」を
    くり返す。書くのが先なので、どの行のレーティングも、書く日より前のレースの結果だけでできている
    （同じ日の先に終わったレースも使わない。設計書 11 の 2）。まだ走っていないレース（着順が欠損値）は、書くだけで更新しない。
    着順の付かなかった馬（競走中止など）は、そのレースの勝ち負けに数えない。

    書く日は、ふつうは開催日（開催日の前日までの結果が入る）。行に材料の締めの日（``as_of_date``。特別登録の予想の登録日相当）が
    あれば、その翌日に書く（締めの日までの結果が入り、締めの日より後の土曜の結果は入らない。特別登録の設計書 11 の 6）。
    更新はいつも開催日に行う。

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
        race_days = ordered["race_date"].to_numpy(dtype="datetime64[D]")
        write_days = self._write_days(ordered, race_days)
        write_order = np.argsort(write_days, kind="stable")
        before = np.empty(len(ordered))
        runs_before = np.empty(len(ordered), dtype=int)
        writes = [(write_days[write_order[start]], write_order[start:end]) for start, end in _slices(write_days[write_order])]
        updates = [(race_days[start], start, end) for start, end in _slices(race_days)]

        def write_ratings(index: int) -> None:
            """その日に書く行に、その時点のレーティングと対戦数を書く。"""
            rows = writes[index][1]
            before[rows] = ratings[horse_codes[rows]]
            runs_before[rows] = counts[horse_codes[rows]]

        def update_ratings(index: int) -> None:
            """その日のレースの着順で、レーティングを更新する。"""
            _, start, end = updates[index]
            self._update_day(race_ids[start:end], start, horse_codes, finishes, ratings, counts)

        steps = {_WRITE: write_ratings, _UPDATE: update_ratings}
        for _, step, index in self._schedule(writes, updates):
            steps[step](index)
        history = pd.DataFrame({
            "race_id": ordered["race_id"].to_numpy(), "horse_id": ordered["horse_id"].to_numpy(),
            "race_date": ordered["race_date"].to_numpy(), RATING: before, RUN_COUNT: runs_before.astype(float),
        }, index=ordered.index)
        return history.loc[runs.index]

    def _schedule(self, writes: list[tuple], updates: list[tuple]) -> list[tuple[np.datetime64, int, int]]:
        """書く日と更新する日を、日の順に1列に並べたもの（日, 手順の種類, その手順の何番目か）。

        同じ日なら、書いてから更新する（書く日より前のレースの結果だけが入る）。
        """
        write_steps = [(day, _WRITE, index) for index, (day, _) in enumerate(writes)]
        update_steps = [(day, _UPDATE, index) for index, (day, _, _) in enumerate(updates)]
        return sorted(write_steps + update_steps)

    def _write_days(self, ordered: pd.DataFrame, race_days: np.ndarray) -> np.ndarray:
        """行ごとの、レーティングを書く日。締めの日があればその翌日、無ければ開催日。"""
        if _AS_OF_DATE not in ordered.columns:
            return race_days
        as_of = pd.to_datetime(ordered[_AS_OF_DATE], errors="coerce").to_numpy(dtype="datetime64[D]")
        has_as_of = ~np.isnat(as_of)
        return np.where(has_as_of, as_of + _ONE_DAY, race_days)

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
