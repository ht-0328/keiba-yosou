"""不利の判定の線と、程度の分け方。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 不利と数える着順（4着以下）。3着以内に来た馬は、不利があっても次走に持ち越さない。
WORST_PLACE = 3
#: 線（設計書「買うレースと買い目を決める」08 の 3 の初めの値）と、程度の段（線からどれだけ超えたかで 小・中・大）。
#: 出遅れ: 実際の序盤の位置 − 見込みの序盤の位置 が 0.4 以上（0.4〜 小、0.5〜 中、0.6〜 大）。
LATE_START_LINE, LATE_START_STEP = 0.4, 0.1
#: 展開が向かなかった: 結果のペースと位置で出した展開スコアが −0.01 以下（−0.01〜 小、−0.02〜 中、−0.03〜 大）。
PACE_LINE, PACE_STEP = -0.01, 0.01
#: バイアスと逆: 結果の位置で出したバイアスの補正が −0.02 以下（−0.02〜 小、−0.03〜 中、−0.04〜 大）。
BIAS_LINE, BIAS_STEP = -0.02, 0.01
#: 程度の最大（大）と、「見直す」にする程度の下限（中）。
MAX_DEGREE, REVIEW_DEGREE = 3, 2


class HandicapLines:
    """値と線から程度（0 なし・1 小・2 中・3 大）を出す。``line`` が正なら「線以上」、負なら「線以下」が不利。
    4着以下でない走は 0。値の無い走は欠損値。"""

    def degree(self, value: pd.Series, finish: pd.Series, line: float, step: float) -> pd.Series:
        over = (value - line) if line > 0 else (line - value)
        raw = np.floor(over / step + 1e-9) + 1   # 0.1 刻みの割り算の丸め（0.0999…）で段が1つ下がらないように
        degree = pd.Series(np.clip(raw, 0, MAX_DEGREE), index=value.index).where(over >= 0, 0.0)
        lost = finish > WORST_PLACE
        return degree.where(lost | finish.isna(), 0.0).where(value.notna() & finish.notna())
