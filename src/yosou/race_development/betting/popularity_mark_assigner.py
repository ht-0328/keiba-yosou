"""比べる基準: 単勝オッズの低い順に印を付ける。"""

from __future__ import annotations

import pandas as pd

from .column_names import HORSE_NO, MARK, NO_MARK, WIN_ODDS
from .mark import RANK_MARKS


class PopularityMarkAssigner:
    """比べる基準。単勝オッズの低い順（同じオッズなら馬番の小さい順）に ◎○▲△ を付ける。☆と注は付けない。

    単勝オッズの無い馬（欠損値）には印を付けない。モデルの印が、人気順の印より良いかを見るために使う（設計書 16 の 8.）。
    """

    def assign(self, race: pd.DataFrame) -> pd.DataFrame:
        """``race`` は1レースの表（列 ``horse_no``・``win_odds``）。

        戻り値は ``race`` に列 ``mark``（印の記号。印の無い馬は空の文字列）を足した表。行の並びと index は ``race`` と同じ。
        """
        marked = race.assign(**{MARK: NO_MARK}).reset_index(drop=True)
        ranked = marked.dropna(subset=[WIN_ODDS]).sort_values([WIN_ODDS, HORSE_NO]).index
        top = ranked[:len(RANK_MARKS)]
        marked.loc[top, MARK] = [mark.value for mark in RANK_MARKS[:len(top)]]
        marked.index = race.index
        return marked
