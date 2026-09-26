"""予想ごとの特徴量の一覧に合わせ、前の組の予測（S・T）の列を足す。"""

from __future__ import annotations

from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import PredictionData, TrainingData

from ..feature import EarlyForecastFeatures, GroupForecast, LateForecastFeatures, StackedColumns
from .development_model_kind import DevelopmentModelKind

_Kind = DevelopmentModelKind
#: 学習データか予測用データ。
Data = TypeVar("Data", TrainingData, PredictionData)
#: 前半の予想の結果（S）を足す予想と、後半の予想の結果（T）を足す予想（設計書 09 の S・T）。
_USES_EARLY = frozenset({_Kind.CORNER4, _Kind.CLOSING, _Kind.LATE_PACE_TIME, _Kind.FINISH})
_USES_LATE = frozenset({_Kind.FINISH})


class KindStacker:
    """1頭ごと（か1レースごと）のデータから、1つの予想のデータを作る（設計書 04 の 1・11 の決まり 11）。

    その予想の特徴量の一覧に列を選び直し、後半と着順の予想には、前の組の予測から作った S・T の列を足す。
    学習データでも予測用データでも同じ手順にし、学習と予測で特徴量の中身がずれないようにする（設計書 11 の 4）。
    """

    def __init__(self) -> None:
        self._stacked_columns = StackedColumns()
        self._early_features = EarlyForecastFeatures()
        self._late_features = LateForecastFeatures()

    def apply(self, kind: DevelopmentModelKind, base: Data, early: GroupForecast | None,
              late: GroupForecast | None) -> Data:
        """S・T が要る予想で、前の組の予測が渡されなければ ``ValueError``。"""
        parts = [self._early_part(kind, base, early), self._late_part(kind, base, late)]
        stacked = [part for part in parts if part is not None]
        extra = pd.concat(stacked, axis=1) if stacked else None
        return self._stacked_columns.apply(base, kind.spec.catalog, extra)

    def _early_part(self, kind: DevelopmentModelKind, base: Data, early: GroupForecast | None) -> pd.DataFrame | None:
        if kind not in _USES_EARLY:
            return None
        if early is None:
            raise ValueError(f"{kind.spec.label_text}には、前半の予想の結果が要ります。")
        if kind.spec.per_race:
            return self._early_features.race(base.ids, early)
        return self._early_features.horse(base.ids, early)

    def _late_part(self, kind: DevelopmentModelKind, base: Data, late: GroupForecast | None) -> pd.DataFrame | None:
        if kind not in _USES_LATE:
            return None
        if late is None:
            raise ValueError(f"{kind.spec.label_text}には、後半の予想の結果が要ります。")
        return self._late_features.horse(base.ids, late)
