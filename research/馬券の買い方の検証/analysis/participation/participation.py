"""買うレースと、広め・少点数の別。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from ..column_names import RACE_ID

BUY_WIDE = "buy_wide"
BUY_NARROW = "buy_narrow"


class Participation:
    """1行 = 1レースの（レースID, 広めで買うか, 少点数で買うか）。両方 True なら両方の買い方で買う。"""

    def __init__(self, race_ids: Sequence[str], wide: Sequence[bool], narrow: Sequence[bool]) -> None:
        if not (len(race_ids) == len(wide) == len(narrow)):
            raise ValueError("レースID と判定の長さが合っていません")
        self._rows = pd.DataFrame({RACE_ID: list(race_ids), BUY_WIDE: [bool(v) for v in wide], BUY_NARROW: [bool(v) for v in narrow]})

    @property
    def rows(self) -> pd.DataFrame:
        return self._rows

    @property
    def wide_ids(self) -> list[str]:
        return list(self._rows[self._rows[BUY_WIDE]][RACE_ID])

    @property
    def narrow_ids(self) -> list[str]:
        return list(self._rows[self._rows[BUY_NARROW]][RACE_ID])

    @property
    def race_count(self) -> int:
        """対象にしたレース数（買わなかったレースも含む）。"""
        return len(self._rows)

    @property
    def selected_count(self) -> int:
        """どちらかで買うレース数。"""
        return int((self._rows[BUY_WIDE] | self._rows[BUY_NARROW]).sum())
