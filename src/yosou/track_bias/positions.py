"""馬番と頭数から内らしさ、位置から前らしさを出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers


class Positions:
    """設計書「買うレースと買い目を決める」06 の 1 の式。

    - 内らしさ u = 0.5 −（馬番 − 1）÷（頭数 − 1）。最内 +0.5、大外 −0.5
    - 前らしさ v = 0.5 − 位置。位置は 0（先頭）〜 1（最後方）で、結果なら（4コーナーの順位 − 1）÷（頭数 − 1）、
      予想なら展開の予想④の値（0 が先頭、1 が最後）

    1頭立て（頭数 − 1 が 0）や、馬番・順位の無い馬は欠損値。例: 16頭立ての2番は 0.5 − 1/15 = 0.433。
    """

    def innerness(self, horse_no: pd.Series, field_size: pd.Series) -> pd.Series:
        return 0.5 - self._fraction(as_numbers(horse_no), as_numbers(field_size))

    def frontness_of_rank(self, corner_rank: pd.Series, field_size: pd.Series) -> pd.Series:
        return 0.5 - self._fraction(as_numbers(corner_rank), as_numbers(field_size))

    def frontness_of_position(self, position: pd.Series) -> pd.Series:
        return 0.5 - as_numbers(position)

    def _fraction(self, rank: pd.Series, field_size: pd.Series) -> pd.Series:
        span = (field_size - 1).where(field_size > 1)
        return (rank - 1) / span
