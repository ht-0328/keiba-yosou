"""1レースで「消」にする危険な人気馬を、人気帯の順に1頭だけ選ぶ。"""

from __future__ import annotations

import pandas as pd

#: 消にできる人気帯（先に書いた人気帯ほど優先）。利用者の決定: 1番人気が危険ならその馬を消にし、1番人気が危険でないレースでは
#: 2〜5番人気から消にする（必ずしも1番人気が危険な人気馬とは限らないため）。
MARKED_BANDS: tuple[str, ...] = ("1番人気", "2〜3番人気", "4〜5番人気")
#: いちばん優先する人気帯。この人気帯の馬が線以上なら、その馬だけを消にする。
_FIRST_BAND = "1番人気"


class DangerPicker:
    """1レースの人気馬の危険度と線から、「消」にする危険な人気馬を1頭だけ選ぶ（設計書「買うレースと買い目を決める」07 の 3）。

    - 1番人気の危険度が線以上なら、1番人気を消にする（ほかの人気帯は見ない）。
    - 1番人気が線未満（または線が無い）なら、``bands`` のほかの人気帯の馬のうち、危険度が線以上の馬から、線をいちばん大きく超えた
      （危険度 − 線がいちばん大きい）馬を消にする。人気帯ごとに線が違うので、危険度そのものではなく線との差で比べる。
    - 線以上の馬がいなければ、消にしない。

    ``bands`` は消にできる人気帯。``("1番人気",)`` なら1番人気だけを消にする（前の決め方。道具「印の成績」で比べるのに使う）。
    """

    def __init__(self, bands: tuple[str, ...] = MARKED_BANDS) -> None:
        self._bands = tuple(bands)

    def pick(self, band: pd.Series, danger: pd.Series, line: pd.Series) -> pd.Series:
        """1レースの人気馬の人気帯・危険度・線（同じ index）から、消にする馬だけ True の列を返す。"""
        margin = (danger.astype(float) - line.astype(float)).where(band.isin(self._bands))
        over = margin[margin >= 0]
        chosen = pd.Series(False, index=band.index)
        if over.empty:
            return chosen
        first = over[band[over.index] == _FIRST_BAND]
        chosen[first.index[0] if not first.empty else over.idxmax()] = True
        return chosen
