"""3つの組（前半・後半・着順）を表す値。"""

from __future__ import annotations

from enum import Enum

from .development_model_kind import DevelopmentModelKind

_Kind = DevelopmentModelKind


class ForecastGroup(Enum):
    """予想の組（設計書 01 の「流れ」）。前の組の予測を、後の組の特徴量に入れる（スタッキング）。

    ``first_train_year`` は、年ごとに学習し直すときの学習データの最初の年（設計書 16 の 7）。後の組は、前の組が
    「その年より前だけで学習した予測」を出し始めた年からしか学習データを作れないので、1年ずつ遅れる。
    """

    EARLY = "early"
    LATE = "late"
    FINISH = "finish"

    @property
    def kinds(self) -> tuple[DevelopmentModelKind, ...]:
        return _KINDS[self]

    @property
    def first_train_year(self) -> int:
        return _FIRST_TRAIN_YEARS[self]

    @property
    def label(self) -> str:
        return _LABELS[self]


_KINDS: dict[ForecastGroup, tuple[DevelopmentModelKind, ...]] = {
    ForecastGroup.EARLY: (_Kind.LEADER, _Kind.POSITION, _Kind.PACE_CLASS, _Kind.PACE_TIME),
    ForecastGroup.LATE: (_Kind.CORNER4, _Kind.CLOSING, _Kind.LATE_PACE_TIME),
    ForecastGroup.FINISH: (_Kind.FINISH, _Kind.FINISH_PLAIN),
}
_FIRST_TRAIN_YEARS: dict[ForecastGroup, int] = {ForecastGroup.EARLY: 2017, ForecastGroup.LATE: 2018, ForecastGroup.FINISH: 2019}
_LABELS: dict[ForecastGroup, str] = {ForecastGroup.EARLY: "前半", ForecastGroup.LATE: "後半", ForecastGroup.FINISH: "着順"}
