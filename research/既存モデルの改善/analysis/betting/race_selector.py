"""勝負するレースを選ぶ（1開催日の上位 N レースと重賞。レースの堅さの帯で絞ることもできる）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE

from .hardness_band import ALL_RACES, HardnessBand
from .race_columns import AXIS_PROBABILITY, FAVORITE_EXCLUDED, GRADED, SCORE


class RaceSelector:
    """買う券種のあるレースから、1開催日ごとに上位 ``per_day`` レースと、重賞を選ぶ。

    - 並べ方: ``excluded_first`` なら、1番人気を消したレース（本当に危険な1番人気がいるレース）を先に、そのあと券種全体の
      期待値の高い順。False なら期待値の高い順だけ（買うレースと買い目を決める の決めごと 3「危険な人気馬を理由にしない」）。
    - 堅さの帯（``band``）: 軸の3着以内の確率が帯に入るレースだけを候補にする。重賞は帯に入らなくても候補に残す
      （重賞はできれば勝負するレースに入れる、という利用者の希望）。
    - 重賞の数え方: ``graded_in_cap`` が False なら、重賞は上位の枠とは別（例: ``per_day`` = 3 で、その日の重賞が
      上位3レースの外にあれば4レースになる）。True なら、重賞を先に並べて上位 ``per_day`` の枠に入れる（1日の合計が
      ``per_day`` を超えない。重賞が枠より多い日は、期待値の高い重賞から）。
    - ``per_day`` が None なら、候補を全部選ぶ。
    """

    def __init__(self, per_day: int | None, band: HardnessBand = ALL_RACES, excluded_first: bool = True,
                 graded_in_cap: bool = False) -> None:
        self._per_day = per_day
        self._band = band
        self._excluded_first = excluded_first
        self._graded_in_cap = graded_in_cap

    def select(self, races: pd.DataFrame) -> pd.Series:
        """レース単位の表（``SCORE`` の列を持つ）の行ごとに、勝負するか。"""
        graded = races[GRADED].fillna(False).astype(bool)
        eligible = graded | self._in_band(races)
        if self._per_day is None:
            return eligible
        ranked = races[eligible if self._graded_in_cap else eligible & ~graded]
        rank = self._rank(ranked).reindex(races.index)
        within = (rank < self._per_day).fillna(False).astype(bool)
        return within if self._graded_in_cap else within | graded

    def _in_band(self, races: pd.DataFrame) -> pd.Series:
        """堅さの帯に入るか。軸の確率の列が無い表では、全部のレースの条件だけが全部を通す。"""
        missing = pd.Series(float("nan"), index=races.index)
        return self._band.contains(races[AXIS_PROBABILITY] if AXIS_PROBABILITY in races.columns else missing)

    def _rank(self, races: pd.DataFrame) -> pd.Series:
        """開催日の中での順位（0 から）。"""
        keys = [RACE_DATE, *([GRADED] if self._graded_in_cap else []),
                *([FAVORITE_EXCLUDED] if self._excluded_first else []), SCORE]
        ascending = [True, *[False] * (len(keys) - 1)]
        ordered = races.sort_values(keys, ascending=ascending, kind="stable")
        return ordered.groupby(RACE_DATE).cumcount()
