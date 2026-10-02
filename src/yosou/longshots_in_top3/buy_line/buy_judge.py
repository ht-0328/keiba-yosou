"""予測の結果に、「買い」の線と「買い」の印を足す。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

#: 足す列の名前（予測の結果の表にも、そのまま出す）。
BUY_LINE = "買いの線"
IS_BUY = "買い"
#: 「買い」の印。
_MARK = "買い"


class BuyJudge:
    """予測の結果に、その馬の区分の「買い」の線と、複勝の期待値がその線以上なら「買い」の印を足す（設計書 16 の 3）。

    ``lines`` は区分の名前（中穴・大穴）→ 複勝の期待値の線。学習のときに検証期間で決めたものか、利用者が
    ``--min-value`` で渡した線。線の無い区分と、期待値の無い馬（木曜・複勝オッズの無い馬）には印を付けない。
    例: 大穴の線が 1.2 で、複勝の期待値 1.26 の大穴は「買い」、1.15 の大穴は印なし。
    """

    def __init__(self, lines: Mapping[str, float]) -> None:
        self._lines = dict(lines)

    def judge(self, value: pd.Series, zone: pd.Series) -> pd.DataFrame:
        """行の並びと index は ``value`` と同じ。``zone`` は行ごとの区分の名前。"""
        line = zone.map(self._lines).astype(float)
        bought = pd.to_numeric(value, errors="coerce") >= line.fillna(np.inf)
        return pd.DataFrame({BUY_LINE: line, IS_BUY: np.where(bought, _MARK, "")}, index=value.index)
