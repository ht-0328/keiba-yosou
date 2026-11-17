"""学習用の表に、2つのモデルの答えの列を足す。"""

from __future__ import annotations

import pandas as pd

from .late_columns import FINAL_ODDS, RACE_ID, WIN_TEACHER, WON

#: 答えの列: 先生（確定オッズを知っている予想）が買う馬か、単勝を 1 買ったときの戻り。
TEACHER_BUYS = "teacher_buys"
RETURN = "win_return"
#: 先生が買うと見る単勝の期待値の線。
TEACHER_VALUE_LINE = 1.0
#: 戻りの上限（倍）。大きな配当に学習が引っぱられないように切る。
RETURN_CAP = 60.0


class LateTargets:
    """先生の 1着の確率はレースの中で合計 1 に直してから確定オッズを掛ける。先生の確率の無い行は ``TEACHER_BUYS`` が欠損になる
    （買う馬らしさのモデルはその行を使わない）。"""

    def attach(self, features: pd.DataFrame) -> pd.DataFrame:
        frame = features.copy()
        share = frame[WIN_TEACHER] / frame.groupby(RACE_ID)[WIN_TEACHER].transform("sum")
        value = share * frame[FINAL_ODDS]
        frame[TEACHER_BUYS] = (value >= TEACHER_VALUE_LINE).astype(float).where(frame[WIN_TEACHER].notna())
        frame[RETURN] = (frame[FINAL_ODDS] * frame[WON]).clip(upper=RETURN_CAP)
        return frame
