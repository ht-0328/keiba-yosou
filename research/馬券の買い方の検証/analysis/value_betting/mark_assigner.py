"""レースごとに印（消・◎・○・▲・△・☆・注）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import columns as c
from .protocol import FIXED_LINE

#: 印の文字。
EXCLUDED_MARK, HONMEI, TAIKOU, TANANA, RENKA, STAR, CHUI = "消", "◎", "○", "▲", "△", "☆", "注"
#: 3着以内の確率の順位 → 印（消を除いて 1位から）。
_RANK_MARKS: dict[int, str] = {1: HONMEI, 2: TAIKOU, 3: TANANA, 4: RENKA, 5: RENKA}
_RACE_KEY = [c.WINDOW, c.PART, c.RACE_ID]
#: ロジットを取るときの端の丸め。
_EDGE = 1e-6


class MarkAssigner:
    """1頭ごとの表（期待値と消の列を持つ）に、レースごとの印を付ける（設計書 買うレースと買い目を決める 07 の 5）。

    - 消: 危険な人気馬（``excluded``）。
    - ◎・○・▲・△: 消を除いて、近走と適性の3着以内の確率が 1・2・3・4〜5位。
    - ☆: 穴馬のうち複勝の期待値が1位で、1.25 以上のときだけ。◎〜△ の付いた馬には付けない（◎〜△ を優先する）。
    - 注: 印の無い馬のうち、上げ下げ（logit(予想の3着以内の確率) − logit(オッズから見た3着以内率)）が最も大きい馬。
    印は表示のためのもので、買う判断は期待値だけで決める。
    """

    def assign(self, runners: pd.DataFrame) -> pd.DataFrame:
        marks = pd.Series("", index=runners.index, dtype=object)
        excluded = runners[c.EXCLUDED].fillna(False).astype(bool)
        marks[excluded] = EXCLUDED_MARK
        remaining = runners[~excluded]
        rank = remaining.groupby(_RACE_KEY)[c.FORM_PROB].rank(method="first", ascending=False)
        ranked = rank.map(_RANK_MARKS).dropna()
        marks[ranked.index] = ranked
        marks = self._with_star(runners, marks)
        return runners.assign(**{c.MARK: self._with_chui(runners, marks).to_numpy()})

    def _with_star(self, runners: pd.DataFrame, marks: pd.Series) -> pd.Series:
        """☆: 穴馬（期待値のある馬）のうち期待値が1位で 1.25 以上、まだ印の無い馬。"""
        holes = runners[(marks == "") & runners[c.PLACE_VALUE].notna()]
        best = holes.groupby(_RACE_KEY)[c.PLACE_VALUE].idxmax()
        chosen = best[runners.loc[best, c.PLACE_VALUE].to_numpy() >= FIXED_LINE]
        marks = marks.copy()
        marks[chosen.to_numpy()] = STAR
        return marks

    def _with_chui(self, runners: pd.DataFrame, marks: pd.Series) -> pd.Series:
        """注: 印の無い馬のうち、上げ下げが最も大きい馬。"""
        unmarked = runners[marks == ""]
        lift = (self._logit(unmarked[c.FORM_PROB]) - self._logit(unmarked[c.MARKET_TOP3])).dropna()
        unmarked = unmarked.loc[lift.index]
        best = lift.groupby([unmarked[key] for key in _RACE_KEY]).idxmax()
        marks = marks.copy()
        marks[best.to_numpy()] = CHUI
        return marks

    def _logit(self, probability: pd.Series) -> pd.Series:
        clipped = probability.astype(float).clip(_EDGE, 1 - _EDGE)
        return np.log(clipped / (1 - clipped))
