"""1レースの馬に印を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .column_names import HORSE_NO, LEADER_PROBABILITY, MARK, NO_MARK, WIN_ODDS, WIN_PROBABILITY
from .mark import RANK_MARKS, Mark

#: ☆ を付ける、単勝の期待値（1着の確率 × 単勝オッズ）の下限。
VALUE_LINE = 1.0


class MarkAssigner:
    """1着の確率・単勝オッズ・先頭の確率から、1レースの馬に ◎○▲△☆注 を付ける（設計書 06 の図4）。

    - ◎○▲△: 1着の確率の 1〜4位（同じ確率なら馬番の小さい順）。4頭に満たなければ、いる馬だけ。
    - ☆: 5位以下の馬のうち、単勝の期待値がいちばん高い馬。期待値が ``value_line``（既定 1.0）以上のときだけ。
      単勝オッズが無い（木曜。欠損値）なら付けない。
    - 注: 印の無い馬のうち、先頭の確率がいちばん高い馬。
    """

    def __init__(self, value_line: float = VALUE_LINE) -> None:
        self._value_line = value_line

    def assign(self, race: pd.DataFrame) -> pd.DataFrame:
        """``race`` は1レースの表（列 ``horse_no``・``win_probability``・``win_odds``・``leader_probability``。取消・除外を除く）。

        戻り値は ``race`` に列 ``mark``（印の記号。印の無い馬は空の文字列）を足した表。行の並びと index は ``race`` と同じ。
        ``win_odds`` の列が無ければ、欠損値の列として足す。
        """
        marked = race.assign(**{WIN_ODDS: race.get(WIN_ODDS, np.nan), MARK: NO_MARK}).reset_index(drop=True)
        ranked = marked.sort_values([WIN_PROBABILITY, HORSE_NO], ascending=[False, True]).index
        top = ranked[:len(RANK_MARKS)]
        marked.loc[top, MARK] = [mark.value for mark in RANK_MARKS[:len(top)]]
        self._mark_value(marked, ranked[len(RANK_MARKS):])
        self._mark_leader(marked)
        marked.index = race.index
        return marked

    def _mark_value(self, marked: pd.DataFrame, rest: pd.Index) -> None:
        """5位以下で単勝の期待値がいちばん高い馬に ☆（線以上のときだけ）。"""
        values = (marked.loc[rest, WIN_PROBABILITY] * marked.loc[rest, WIN_ODDS]).dropna()
        if values.empty or values.max() < self._value_line:
            return
        marked.loc[values.idxmax(), MARK] = Mark.VALUE.value

    def _mark_leader(self, marked: pd.DataFrame) -> None:
        """印の無い馬のうち、先頭の確率がいちばん高い馬に 注。"""
        leaders = marked.loc[marked[MARK] == NO_MARK, LEADER_PROBABILITY].dropna()
        if leaders.empty:
            return
        marked.loc[leaders.idxmax(), MARK] = Mark.LEADER.value
