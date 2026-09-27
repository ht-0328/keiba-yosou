"""予想ごとの学習データを、1頭ごとと1レースごとの学習データから作る。"""

from __future__ import annotations

from yosou.shared.dataset import TrainingData

from ..feature import PriorForecasts
from ..tendency import TendencyDatasets
from .development_model_kind import DevelopmentModelKind
from .kind_stacker import KindStacker


class KindDatasets:
    """元DB から1回ずつ作った1頭ごと・1レースごとの学習データから、予想ごとの学習データを作る（設計書 04 の 1・08 の 4）。

    予想ごとの特徴量の一覧に列を選び直し、前の組の予測（V・S・T）の列を足す（``KindStacker``）。
    前の組の予測が無い行（前の組が予測を出していない年）は外れる。目的変数は、まだ持ち替えない（``labeled`` で持ち替える）。
    傾向の組が学ぶ既存の予想の学習データ（``tendency``）も、一緒に持つ。
    """

    def __init__(self, horses: TrainingData, races: TrainingData, tendency: TendencyDatasets) -> None:
        self._horses = horses
        self._races = races
        self._tendency = tendency
        self._stacker = KindStacker()

    @property
    def horses(self) -> TrainingData:
        return self._horses

    @property
    def races(self) -> TrainingData:
        return self._races

    @property
    def tendency(self) -> TendencyDatasets:
        return self._tendency

    def of(self, kind: DevelopmentModelKind, priors: PriorForecasts) -> TrainingData:
        """その予想の特徴量の学習データ（目的変数は持ち替えていない）。"""
        base = self._races if kind.spec.per_race else self._horses
        return self._stacker.apply(kind, base, priors)

    def labeled(self, kind: DevelopmentModelKind, data: TrainingData) -> TrainingData:
        """目的変数をその予想の列に持ち替え、目的変数の無い行を外す。"""
        return data.with_label(kind.spec.label, kind.spec.class_labels)
