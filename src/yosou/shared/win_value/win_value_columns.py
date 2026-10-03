"""予測の結果に足す、単勝の期待値の列。"""

from __future__ import annotations

import pandas as pd

from ..dataset import PredictionData
from ..dataset.column_names import WIN_ODDS
from .win_expected_value import WinExpectedValue


class WinValueColumns:
    """1着を当てる予想の予測の結果に足す列を作る（設計書「近走と適性から3着以内を予想」の 15 の 14）。

    - 単勝の期待値: オッズが分かる時点（前日・当日）だけ。単勝オッズは、予測用データの ``market``（予測に使ったオッズ）から取る。
    木曜（オッズが無い。1着の基準も無い）は何も足さない（複勝の期待値の ``PlaceValueColumns`` と同じ決まり）。
    """

    def __init__(self) -> None:
        self._value = WinExpectedValue()

    def of(self, win_probability: pd.Series, data: PredictionData) -> pd.DataFrame:
        """``data`` は1着のモデル用の予測用データ（基準はオッズから見た勝率）。行の並びと index は ``data.ids`` と同じ。"""
        if data.baseline is None or data.market is None or WIN_ODDS not in data.market.columns:
            return pd.DataFrame(index=data.ids.index)
        return self._value.of(win_probability, data.market[WIN_ODDS]).to_frame()
