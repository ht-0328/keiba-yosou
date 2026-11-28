"""レースごとの ◎ と、公開ルールの線で買うかを決める。"""

from __future__ import annotations

import pandas as pd

#: ◎ の候補にする単勝オッズの上限（倍。印の決まりと同じ）。
TOP_CANDIDATE_ODDS = 30.0


class TopPicks:
    """1頭1行の表から、レースごとの ◎（単勝オッズ ``TOP_CANDIDATE_ODDS`` 倍以下で、1着の確率 × 単勝オッズ（期待値）がいちばん高い馬）を1行ずつ選ぶ。
    ``bought`` は、そのうち期待値が線以上・単勝オッズが上限以下の行（公開ルールで買うレース）。

    ``of`` の列は ``race_id``・``day``・``year``・``p``（その時点の1着の確率）・``odds``（その時点の単勝オッズ）・``win_pay``（確定の単勝の払戻。外れは 0）。
    返す表に ``value``（期待値）を足す。払戻は、どの時点で選んでも確定の払戻（買った時点のオッズではなく、締め切りのオッズで払われる）。
    """

    def of(self, horses: pd.DataFrame) -> pd.DataFrame:
        candidates = horses[horses["odds"].notna() & (horses["odds"] <= TOP_CANDIDATE_ODDS)]
        candidates = candidates.assign(value=candidates["p"] * candidates["odds"])
        return candidates.loc[candidates.groupby("race_id")["value"].idxmax()].reset_index(drop=True)

    @staticmethod
    def bought(tops: pd.DataFrame, value_line: float, odds_cap: float) -> pd.DataFrame:
        return tops[(tops["value"] >= value_line) & (tops["odds"] <= odds_cap)]
