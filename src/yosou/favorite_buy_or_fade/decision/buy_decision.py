"""3つの近さの点数から、1番人気をどう扱うかを決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..dataset import IN_THE_MONEY, OUT_OF_THE_MONEY, WIN
from ..similarity import SCORE_COLUMNS
from .bet_kinds import DECISION, FADE, PLACE_ONLY, WIN_AND_PLACE


class BuyDecision:
    """判定（設計書 13・06 の図2）。点数を比べて、文字どおり「どちらに近いか」で決める。

    1. 馬券外の近さが、馬券内の近さより ``fade_margin`` を超えて高ければ「消す」。
    2. 消さなかった馬は、勝利の近さが、馬券内の近さより ``win_margin`` を超えて高ければ「単勝と複勝」、
       そうでなければ「複勝だけ」。
    点数が同じ（差が線ちょうど）なら、消さない・単勝を足さない側にする（何でもかんでも切らないため）。
    """

    def __init__(self, fade_margin: float, win_margin: float) -> None:
        self._fade_margin = fade_margin
        self._win_margin = win_margin

    def decide(self, scores: pd.DataFrame) -> pd.Series:
        """行ごとの判定。``scores`` は ``SCORE_COLUMNS`` の3つの列を持つ表。"""
        in_the_money = scores[SCORE_COLUMNS[IN_THE_MONEY]]
        fade = scores[SCORE_COLUMNS[OUT_OF_THE_MONEY]] - in_the_money > self._fade_margin
        win = scores[SCORE_COLUMNS[WIN]] - in_the_money > self._win_margin
        kinds = np.select([fade, win], [FADE, WIN_AND_PLACE], default=PLACE_ONLY)
        return pd.Series(kinds, index=scores.index, name=DECISION, dtype=object)
