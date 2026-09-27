"""ペースの測り方を3通り並べる。"""

from __future__ import annotations

import pandas as pd

from .condition_pace_measure import ConditionPaceMeasure
from .pace_bands import PaceBands
from .race_pace_classifier import PACE_Z

#: 前半と後半の差の列（秒。前3ハロン − 後3ハロン。マイナスなら前半のほうが速い）。
HALF_GAP = "前後半の差（秒）"
#: 比べる測り方の名前（区分の列の名前にもなる）。
FIRST_HALF, FIRST_HALF_BY_CONDITION, HALF_BALANCE = "前半の速さ", "前半の速さ（馬場状態あり）", "前後半の差（馬場状態あり）"
MEASURES: tuple[str, ...] = (FIRST_HALF, FIRST_HALF_BY_CONDITION, HALF_BALANCE)


class PaceMeasureTable:
    """``RacePaceClassifier`` を通したレースの表に、測り方ごとの z と区分を足す。

    - 前半の速さ: 手順1の測り方（前3ハロンを、馬場状態を分けない基準と比べる）。
    - 前半の速さ（馬場状態あり）: 前3ハロンを、馬場状態も同じレースの基準と比べる。
    - 前後半の差（馬場状態あり）: 前3ハロン − 後3ハロンを、馬場状態も同じレースの基準と比べる。前半だけ速くて中盤で緩み、
      後半も速くなったレースはハイになりにくい。
      例: 基準の差が −0.5秒のコースで、前半 34.0・後半 36.0（差 −2.0秒）なら、前半に偏って速いのでハイ。

    列の名前は、z が ``<測り方>（z）``、区分が ``<測り方>``。
    """

    def __init__(self) -> None:
        self._bands = PaceBands()

    def build(self, races: pd.DataFrame) -> pd.DataFrame:
        gap = pd.to_numeric(races["first3f"], errors="coerce") - pd.to_numeric(races["last3f_race"], errors="coerce")
        with_gap = races.assign(**{HALF_GAP: gap})
        zs = {
            FIRST_HALF: races[PACE_Z],
            FIRST_HALF_BY_CONDITION: ConditionPaceMeasure("first3f").z(with_gap),
            HALF_BALANCE: ConditionPaceMeasure(HALF_GAP).z(with_gap),
        }
        columns = {}
        for name, z in zs.items():
            columns[f"{name}（z）"] = z
            columns[name] = self._bands.label(z)
        return with_gap.assign(**columns)
