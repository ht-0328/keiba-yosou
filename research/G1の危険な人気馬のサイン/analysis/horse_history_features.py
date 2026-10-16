"""馬ごとの、今回より前の出走から作るサインの材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .sign_columns import (
    BEST_PLACED_DISTANCE_GAP,
    DISTANCE_STEP_UP,
    G1_BEST_FINISH,
    G1_PLACES,
    G1_RUNS,
    GRADED_PLACES,
    GRADED_WINS,
    LAST5_NEAR_MISSES,
    LAST5_WINS,
    PREV2_FINISH,
    PREV_CLASS_ORDER,
    RUNS_SINCE_WIN,
    SAME_STAKES_PLACES,
    SAME_STAKES_RUNS,
    WINS,
)

#: 平地の G1・G2・G3 のグレードコード（障害の重賞は F・G・H で、ここには入れない）。
G1_GRADE = "A"
_LOWER_GRADES = ("B", "C")
#: 「惜しい競馬」とみなす着順の幅。
_NEAR_MISS = (2, 5)
#: 近走として見る走の数。
_RECENT_RUNS = 5


class HorseHistoryFeatures:
    """1行 = 1頭の出走の表（``RunHistoryRepository``）から、その出走より前の走だけで作る材料の列を返す（同じ並びの index）。

    今回の走の結果は使わない（どの列も、同じ馬の前の走までの累積・1つ前・2つ前の値）。DB にある中央の走だけを数える
    （2011年より前の走・地方・海外の走は入らない）。
    """

    def compute(self, runs: pd.DataFrame) -> pd.DataFrame:
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"])
        horse = ordered["horse_id"]
        finish = ordered["finish"]
        placed, won = finish.le(3), finish.eq(1)
        is_g1 = ordered["grade_code"].eq(G1_GRADE)
        is_graded = ordered["grade_code"].isin((G1_GRADE, *_LOWER_GRADES))
        out = pd.DataFrame(index=ordered.index)
        out[WINS] = self._before(won, horse)
        out[G1_RUNS] = self._before(is_g1, horse)
        out[G1_PLACES] = self._before(is_g1 & placed, horse)
        out[G1_BEST_FINISH] = self._best_before(finish.where(is_g1), horse)
        out[GRADED_WINS] = self._before(ordered["grade_code"].isin(_LOWER_GRADES) & won, horse)
        out[GRADED_PLACES] = self._before(is_graded & placed, horse)
        out[BEST_PLACED_DISTANCE_GAP] = ordered["distance_m"] - self._longest_placed_before(ordered, placed)
        out[DISTANCE_STEP_UP] = ordered["distance_m"] - ordered["prev_distance_m"]
        out[SAME_STAKES_RUNS], out[SAME_STAKES_PLACES] = self._same_stakes_before(ordered, placed)
        out[LAST5_NEAR_MISSES], out[LAST5_WINS] = self._recent(finish, horse)
        out[RUNS_SINCE_WIN] = self._runs_since_win(won, horse)
        out[PREV2_FINISH] = finish.groupby(horse).shift(2)
        out[PREV_CLASS_ORDER] = ordered["class_order"].groupby(horse).shift(1)
        return out.reindex(runs.index)

    def _before(self, flag: pd.Series, horse: pd.Series) -> pd.Series:
        """前の走までに、``flag`` が真だった走の数。"""
        counts = flag.astype(int)
        return counts.groupby(horse).cumsum() - counts

    def _best_before(self, finish: pd.Series, horse: pd.Series) -> pd.Series:
        """前の走までの、``finish`` の最小（値のある走が無ければ NaN）。"""
        best = finish.groupby(horse).cummin().groupby(horse).ffill()
        return best.groupby(horse).shift(1)

    def _longest_placed_before(self, ordered: pd.DataFrame, placed: pd.Series) -> pd.Series:
        """前の走までに、同じ芝ダで3着以内に来たいちばん長い距離（無ければ NaN）。"""
        keys = [ordered["horse_id"], ordered["surface"]]
        longest = ordered["distance_m"].where(placed).groupby(keys).cummax().groupby(keys).ffill()
        return longest.groupby(keys).shift(1)

    def _same_stakes_before(self, ordered: pd.DataFrame, placed: pd.Series) -> tuple[pd.Series, pd.Series]:
        """同じ重賞（特別競走番号）への前の出走数と、そこでの3着以内の数。重賞でない走は NaN。"""
        stakes = ordered["stakes_no"]
        rows = stakes.notna()
        keys = [ordered.loc[rows, "horse_id"], stakes[rows]]
        runs = pd.Series(np.nan, index=ordered.index)
        places = pd.Series(np.nan, index=ordered.index)
        runs[rows] = ordered.loc[rows, "horse_id"].groupby(keys).cumcount()
        flag = placed[rows].astype(int)
        places[rows] = flag.groupby(keys).cumsum() - flag
        return runs, places

    def _recent(self, finish: pd.Series, horse: pd.Series) -> tuple[pd.Series, pd.Series]:
        """近5走（前の走から5つ）の 2〜5着の数と1着の数。"""
        grouped = finish.groupby(horse)
        previous = [grouped.shift(step) for step in range(1, _RECENT_RUNS + 1)]
        near = sum(value.between(*_NEAR_MISS).astype(int) for value in previous)
        wins = sum(value.eq(1).astype(int) for value in previous)
        return near, wins

    def _runs_since_win(self, won: pd.Series, horse: pd.Series) -> pd.Series:
        """最後に勝ってから今回までに走った数（勝ったことが無ければ、前の走の数）。"""
        number = won.groupby(horse).cumcount()
        last_win = number.where(won).groupby(horse).ffill().groupby(horse).shift(1)
        return (number - last_win - 1).fillna(number)
