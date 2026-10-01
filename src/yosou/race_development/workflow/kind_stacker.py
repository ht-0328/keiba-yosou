"""予想ごとの特徴量の一覧に合わせ、前の組の予測（V・S・T）の列を足す。"""

from __future__ import annotations

from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import PredictionData, TrainingData

from ..feature import (
    REQUIRED_HORSE_FEATURES,
    REQUIRED_RACE_FEATURES,
    EarlyForecastFeatures,
    LateForecastFeatures,
    OddsComparisonFeatures,
    PriorForecasts,
    StackedColumns,
    TendencyFeatures,
)
from .development_model_kind import DevelopmentModelKind

_Kind = DevelopmentModelKind
#: 学習データか予測用データ。
Data = TypeVar("Data", TrainingData, PredictionData)
#: 着順の組の予想（⑦ と、比べるためだけの予想）。
_FINISH_KINDS = frozenset({_Kind.FINISH, _Kind.FINISH_PLAIN, _Kind.FINISH_NO_EARLY, _Kind.FINISH_NO_LATE, _Kind.FINISH_WITH_ODDS})
#: 前半の予想の結果（S）を足す予想と、後半の予想の結果（T）を足す予想（設計書 09 の S・T）。
#: 傾向の組の結果（V）は、すべての予想に足す（設計書 09 の V）。
#: 着順の組は、S・T を使わない比べるための予想にも足す。どの列を使うかは特徴量の一覧が決めるので、足しても使われないが、
#: S・T のそろった同じ行で学習・評価するため（比べる相手と学習データの行がずれないように）。
_USES_EARLY = frozenset({_Kind.CORNER4, _Kind.CLOSING, _Kind.LATE_PACE_TIME}) | _FINISH_KINDS
_USES_LATE = _FINISH_KINDS
#: オッズ（W）を足す予想（年ごとの確かめで比べるためだけ。設計書 16 の 3）。
_USES_ODDS = frozenset({_Kind.FINISH_WITH_ODDS})


class KindStacker:
    """1頭ごと（か1レースごと）のデータから、1つの予想のデータを作る（設計書 04 の 1・11 の決まり 11）。

    その予想の特徴量の一覧に列を選び直し、どの予想にも傾向の組の予測から作った V の列を、後半と着順の予想には
    前半・後半の組の予測から作った S・T の列を足す。学習データでも予測用データでも同じ手順にし、
    学習と予測で特徴量の中身がずれないようにする（設計書 11 の 4）。
    """

    def __init__(self) -> None:
        self._stacked_columns = StackedColumns()
        self._tendency_features = TendencyFeatures()
        self._early_features = EarlyForecastFeatures()
        self._late_features = LateForecastFeatures()
        self._odds_features = OddsComparisonFeatures()

    def apply(self, kind: DevelopmentModelKind, base: Data, priors: PriorForecasts) -> Data:
        """V・S・T が要る予想で、前の組の予測が渡されなければ ``ValueError``。"""
        tendency = self._tendency_part(kind, base, priors)
        parts = [part for part in (self._early_part(kind, base, priors), self._late_part(kind, base, priors))
                 if part is not None]
        available = tendency[self._required(kind)].notna().all(axis=1)
        for part in parts:
            available &= part.notna().all(axis=1)
        extra = pd.concat([tendency, *parts, *self._odds_part(kind, base)], axis=1)
        return self._stacked_columns.apply(base, kind.spec.catalog, extra, available)

    def _tendency_part(self, kind: DevelopmentModelKind, base: Data, priors: PriorForecasts) -> pd.DataFrame:
        if priors.tendency is None:
            raise ValueError(f"{kind.spec.label_text}には、既存の予想（傾向の組）の結果が要ります。")
        if kind.spec.per_race:
            return self._tendency_features.race(base.ids, priors.tendency)
        return self._tendency_features.horse(base.ids, priors.tendency)

    def _required(self, kind: DevelopmentModelKind) -> list[str]:
        """V のうち、値が無い行を学習データから外す列（人気馬・穴馬の確率は、欠損値が普通なので入れない）。"""
        return list(REQUIRED_RACE_FEATURES if kind.spec.per_race else REQUIRED_HORSE_FEATURES)

    def _early_part(self, kind: DevelopmentModelKind, base: Data, priors: PriorForecasts) -> pd.DataFrame | None:
        if kind not in _USES_EARLY:
            return None
        if priors.early is None:
            raise ValueError(f"{kind.spec.label_text}には、前半の予想の結果が要ります。")
        if kind.spec.per_race:
            return self._early_features.race(base.ids, priors.early)
        return self._early_features.horse(base.ids, priors.early)

    def _odds_part(self, kind: DevelopmentModelKind, base: Data) -> list[pd.DataFrame]:
        """W の列（オッズを足す予想の学習データだけ）。オッズの欠けた行は欠損値のまま（行は外さない）。"""
        if kind not in _USES_ODDS:
            return []
        if not isinstance(base, TrainingData):
            raise ValueError(f"{kind.spec.label_text}は、年ごとの確かめで比べるためだけの予想で、予測には使えません。")
        return [self._odds_features.horse(base.evaluation)]

    def _late_part(self, kind: DevelopmentModelKind, base: Data, priors: PriorForecasts) -> pd.DataFrame | None:
        if kind not in _USES_LATE:
            return None
        if priors.late is None:
            raise ValueError(f"{kind.spec.label_text}には、後半の予想の結果が要ります。")
        return self._late_features.horse(base.ids, priors.late)
