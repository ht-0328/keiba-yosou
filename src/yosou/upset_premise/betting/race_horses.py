"""1レースの出走馬ごとの予想（1着の確率と3着以内の確率）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RaceHorses:
    """1レースの出走馬ごとの、1着の確率（``win``）と3着以内の確率（``top3``）。並びは馬番の並びと同じ。

    1着の確率は、レースの中で合計 1 になるように直した値を持つ（組の確率を Harville の式で作るため）。
    ``usual_top3`` は今の予想（全部のレースで学んだ手本の予想）の3着以内の確率。一律の買い方が、2着・3着の重みに使う
    （設計書 15 の 6）。無ければ None（甲・乙・丙は使わない）。
    """

    race_id: str
    horse_numbers: np.ndarray
    win: np.ndarray
    top3: np.ndarray
    usual_top3: np.ndarray | None = None

    def __post_init__(self) -> None:
        if not (len(self.horse_numbers) == len(self.win) == len(self.top3)):
            raise ValueError(f"{self.race_id}: 馬番と確率の数がそろっていません")
        if self.usual_top3 is not None and len(self.usual_top3) != len(self.horse_numbers):
            raise ValueError(f"{self.race_id}: 馬番と今の予想の確率の数がそろっていません")

    def by_win(self, count: int) -> list[int]:
        """1着の確率の高い順に ``count`` 頭の馬番。"""
        return self._top(self.win, count)

    def by_top3(self, count: int) -> list[int]:
        """3着以内の確率の高い順に ``count`` 頭の馬番。"""
        return self._top(self.top3, count)

    def win_of(self) -> dict[int, float]:
        """馬番 → 1着の確率。"""
        return dict(zip(self.horse_numbers.tolist(), self.win.tolist()))

    def place_of(self) -> dict[int, float]:
        """馬番 → 2着・3着の重み（設計書 15 の 6）。

        今の予想の3着以内の確率があれば、荒れる前提の3着以内の確率との平均。無ければ荒れる前提の3着以内の確率。
        """
        weights = self.top3 if self.usual_top3 is None else (self.top3 + self.usual_top3) / 2.0
        return dict(zip(self.horse_numbers.tolist(), weights.tolist()))

    def _top(self, values: np.ndarray, count: int) -> list[int]:
        # 同じ値なら馬番の小さいほうを先にする（並べ替えを安定にする）
        order = np.lexsort((self.horse_numbers, -values))
        return self.horse_numbers[order[:count]].tolist()
