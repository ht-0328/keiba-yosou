"""3回目の材料表（1頭ごと・1レースごと・払戻の履歴）を持つ値。"""

from __future__ import annotations

import pandas as pd

from . import columns as c


class Round3Materials:
    """7つの区切りの予測をまとめた材料。

    - ``runners``: 1行 = 1頭 × 区切り × 期間（``RunnerTableBuilder`` の列）。
    - ``races``: 1行 = 1レース × 区切り × 期間（``RaceTableBuilder`` の列）。
    - ``price_history``: 複勝の見込みの倍率を決めるための、全頭・全期間の履歴（開催日・複勝オッズの最低と最高・複勝の払戻）。
      予測の有無によらず、学習データの表の全行。
    """

    def __init__(self, runners: pd.DataFrame, races: pd.DataFrame, price_history: pd.DataFrame) -> None:
        self._runners = runners.reset_index(drop=True)
        self._races = races.reset_index(drop=True)
        self._price_history = price_history.reset_index(drop=True)

    @property
    def runners(self) -> pd.DataFrame:
        return self._runners

    @property
    def races(self) -> pd.DataFrame:
        return self._races

    @property
    def price_history(self) -> pd.DataFrame:
        return self._price_history

    @property
    def window_names(self) -> list[str]:
        """材料にある区切りの名前（出てくる順）。"""
        return list(dict.fromkeys(self._runners[c.WINDOW]))

    def runners_of(self, window: str, part: str) -> pd.DataFrame:
        """その区切り・その期間（検証かテスト）の1頭ごとの行。"""
        rows = self._runners
        return rows[(rows[c.WINDOW] == window) & (rows[c.PART] == part)]

    def races_of(self, window: str, part: str) -> pd.DataFrame:
        """その区切り・その期間のレースごとの行。"""
        rows = self._races
        return rows[(rows[c.WINDOW] == window) & (rows[c.PART] == part)]
