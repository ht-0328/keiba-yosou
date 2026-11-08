"""対象レースで使う確率。"""

from __future__ import annotations

from enum import Enum

from yosou.shared.feature import PredictionTiming


class LegModel(Enum):
    """対象レースで使う1着の確率（設計書 06 の図1、07 の「対象レースごとの確率の選び方」）。

    - 今のモデルの当日: 馬体重と馬場状態が出ているレース。
    - 今のモデルの前日: 締め切り前のオッズと馬番はあるが、馬体重がまだのレース。
    - オッズだけ: 障害のレース（今のモデルは障害を予想しない）。オッズから見た勝率をそのまま使う。
    """

    RACE_DAY = "当日"
    DAY_BEFORE = "前日"
    ODDS_ONLY = "オッズだけ"

    @property
    def label(self) -> str:
        """表に出す名前。"""
        return self.value

    @property
    def timing(self) -> PredictionTiming | None:
        """今のモデルの時点。オッズだけは None。"""
        return _TIMINGS.get(self)


_TIMINGS: dict[LegModel, PredictionTiming] = {
    LegModel.RACE_DAY: PredictionTiming.RACE_DAY,
    LegModel.DAY_BEFORE: PredictionTiming.DAY_BEFORE,
}
