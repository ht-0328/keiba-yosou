"""1つの券種の型の候補を全部、年ごとの組の表で数え上げて、候補ごとのセル × 開催日の集計にする。"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from .combos_source import CombosSource
from .day_table import VALUE_COUNT, DayTable
from .formation import Formation
from .formation_mask import FormationMask
from .ticket_picker import TicketPicker

#: 保存するファイルの中身（``np.savez``）。
VALUES, CELLS, DAYS, LABELS = "values", "cells", "days", "labels"


class CandidateCounter:
    """券種 ``label`` の型の候補（``formations``）ごとに、``years`` の組の表（``CombosSource.load``）で買う組を決め（``FormationMask`` → ``TicketPicker``）、
    セル × 開催日の点数・払戻・レース数・当たったレース数（``DayTable``）に足し込む（docs/01 の 4）。

    結果は配列 [候補, セル, 開催日, 4]。``save(path)`` で ``npz`` に書く（候補の名前・セル・開催日も一緒に）。
    組の表は年ごとに1回だけ読み、候補の数だけ判定を回す。
    """

    def __init__(self, source: CombosSource, label: str, formations: Sequence[Formation], cells: Sequence[str],
                 days: Sequence[pd.Timestamp]) -> None:
        self._source = source
        self._label = label
        self._formations = tuple(formations)
        self._cells = tuple(cells)
        self._days = tuple(pd.Timestamp(day) for day in days)
        self._mask = FormationMask.of(label)
        self._picker = TicketPicker()
        self.tables = [DayTable(self._cells, self._days) for _ in self._formations]

    def count(self, years: Sequence[int]) -> np.ndarray:
        for year in years:
            started = time.monotonic()
            combos = self._source.load(self._label, year)
            for formation, table in zip(self._formations, self.tables, strict=True):
                in_formation = self._mask.of_rows(combos, formation)
                chosen = self._picker.pick(combos, in_formation, formation.value_line, formation.max_points)
                table.add(combos, chosen)
            print(f"  {self._label} {year}: 組 {len(combos):,}・レース {combos['race_id'].nunique():,}（{time.monotonic() - started:.0f}秒）",
                  file=sys.stderr, flush=True)
        return self.values()

    def values(self) -> np.ndarray:
        """配列 [候補, セル, 開催日, 4]。"""
        if not self.tables:
            return np.zeros((0, len(self._cells), len(self._days), VALUE_COUNT))
        return np.stack([table.values for table in self.tables], axis=0)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **{VALUES: self.values(), CELLS: np.array(self._cells, dtype=object),
                                      DAYS: np.array([day.isoformat() for day in self._days]),
                                      LABELS: np.array([formation.label for formation in self._formations], dtype=object)})
        return path

    @staticmethod
    def load(path: Path) -> tuple[np.ndarray, list[str], list[pd.Timestamp], list[str]]:
        """``save`` したものを戻す（配列・セル・開催日・候補の名前）。"""
        saved = np.load(path, allow_pickle=True)
        return (saved[VALUES], [str(cell) for cell in saved[CELLS]], [pd.Timestamp(str(day)) for day in saved[DAYS]],
                [str(label) for label in saved[LABELS]])
