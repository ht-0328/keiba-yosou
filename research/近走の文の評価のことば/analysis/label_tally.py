"""ことばごとの次走の成績を数える。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.popularity_expectation import PopularityExpectation

#: 採用の線: 人気から見た差が、標準誤差のこの倍以上（ことばの向きに）。
ADOPT_SIGMAS = 2.0


@dataclass(frozen=True)
class LabelRow:
    """1つのことばの成績。率と差はポイント（%）。``adopted`` は採用の線を満たすか（参考のことばは None）。"""

    label: str
    runs: int
    place_rate: float
    gap_points: float
    std_error_points: float
    win_return: float
    place_return: float
    adopted: bool | None


class LabelTally:
    """走の表（``placed``・``finish``・``popularity``・``win_payout``・``place_payout``）と、ことばの真偽の列から、
    ことばごとに、付いた走の数・3着以内率・人気から見た差（``PopularityExpectation``。期待は渡した走の全体）・差の標準誤差・単勝と複勝の回収率を数える。
    """

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame.assign(first=frame["finish"] == 1, second=frame["finish"] == 2, third=frame["finish"] == 3)
        self._expectation = PopularityExpectation(self._frame)

    def rows(self, labels: pd.DataFrame, sides: dict[str, bool | None]) -> list[LabelRow]:
        """``labels`` の列ごとに1行。``sides`` は列 → 向き（True 良い・False 悪い・None 参考）。"""
        return [self._row(name, labels[name], sides.get(name)) for name in labels.columns]

    def _row(self, name: str, flag: pd.Series, side: bool | None) -> LabelRow:
        chosen = self._frame[flag.to_numpy()]
        count = len(chosen)
        if count == 0:
            return LabelRow(name, 0, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"), None)
        gap = self._expectation.top3_gap(chosen)
        win_return = chosen["win_payout"].fillna(0).sum() / (100 * count) * 100
        place_return = chosen["place_payout"].fillna(0).sum() / (100 * count) * 100
        adopted = None
        if side is not None and gap.runs > 0:
            adopted = (gap.gap >= ADOPT_SIGMAS * gap.std_error) if side else (gap.gap <= -ADOPT_SIGMAS * gap.std_error)
        return LabelRow(name, count, chosen["placed"].mean() * 100, gap.gap * 100, gap.std_error * 100, win_return, place_return, adopted)
