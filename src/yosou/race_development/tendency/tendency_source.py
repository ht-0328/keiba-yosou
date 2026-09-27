"""展開の予想の材料にする、既存の4つの予想。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum

import duckdb

from yosou.favorites_out_of_top3.dataset import dataset_builder as favorites_dataset_builder
from yosou.favorites_out_of_top3.workflow import SEGMENTS as FAVORITE_SEGMENTS
from yosou.favorites_out_of_top3.workflow import TIMINGS as FAVORITE_TIMINGS
from yosou.form_aptitude_top3.dataset import dataset_builder as form_dataset_builder
from yosou.longshots_in_top3.dataset import dataset_builder as longshots_dataset_builder
from yosou.longshots_in_top3.workflow import SEGMENTS as LONGSHOT_SEGMENTS
from yosou.shared.dataset import DatasetBuilder, PredictionData, RaceDatasetBuilder
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, MEMBER_TYPES
from yosou.shared.workflow import ModelSegments
from yosou.upset_level.dataset import BetType
from yosou.upset_level.dataset import race_dataset_builder as upset_dataset_builder

from ..feature import FAVORITE_OUT_PROBABILITY, LONGSHOT_TOP3_PROBABILITY, TOP3_PROBABILITY, UPSET_BETS
from .probability_output import ProbabilityOutput
from .tendency_unit import TendencyUnit
from .upset_output import UpsetOutput

if {bet.key: bet.label for bet in BetType} != UPSET_BETS:
    raise ImportError("荒れ具合の券種が、既存の予想「荒れ具合」の券種と合っていません")

#: 前日からの時点（人気とオッズが決まってから）。
_WITH_ODDS = (PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY)


@dataclass(frozen=True)
class TendencySpec:
    """1つの既存の予想の決めごと。

    - ``label``: 表に出す名前。
    - ``per_race``: 1行 = 1レースの予想か（False なら 1行 = 1頭）。
    - ``builder``: 元DB への接続から、既存の予想の学習データ・予測用データを作るクラスを組み立てる関数（既存の予想のもの）。
    - ``timings``: 予測を出す時点。既存の予想がモデルを持たない時点は、その列を欠損値にする。
    - ``units``: 別々に学ぶモデル（区分・券種ごと）。
    """

    label: str
    per_race: bool
    builder: Callable[[duckdb.DuckDBPyConnection], DatasetBuilder | RaceDatasetBuilder]
    timings: tuple[PredictionTiming, ...]
    units: tuple[TendencyUnit, ...]


class TendencySource(Enum):
    """展開の予想の材料にする、既存の4つの予想（設計書 01 の「流れ」の傾向の組）。値は、モデルと学習データの置き場所の名前。"""

    FORM_TOP3 = "form_aptitude_top3"
    FAVORITES_OUT = "favorites_out_of_top3"
    LONGSHOTS_IN = "longshots_in_top3"
    UPSET_LEVEL = "upset_level"

    @property
    def spec(self) -> TendencySpec:
        return _SPECS[self]

    def predicts_at(self, timing: PredictionTiming) -> bool:
        """その時点で予測を出すか。"""
        return timing in self.spec.timings

    def prediction_data(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
                        popularity: Mapping[int | str, int] | None,
                        odds: Mapping[int, float] | None) -> PredictionData:
        """1レースの、この既存の予想の予測用データ。人気は1頭ごとの予想（人気馬・穴馬の行の選び方）だけが使う。"""
        builder = self.spec.builder(con)
        if isinstance(builder, RaceDatasetBuilder):
            return builder.build_prediction_data(race_id, timing, odds=odds)
        return builder.build_prediction_data(race_id, timing, popularity, odds)


def _segment_units(segments: ModelSegments, column: str) -> tuple[TendencyUnit, ...]:
    """区分ごとのモデル（区分の名前 → フォルダは、既存の予想の分け方のまま）。"""
    return tuple(
        TendencyUnit(folder, MEMBER_TYPES, ProbabilityOutput(column), segments, label)
        for label, folder in segments.folders.items()
    )


_SPECS: dict[TendencySource, TendencySpec] = {
    TendencySource.FORM_TOP3: TendencySpec(
        "近走と適性から3着以内", False, form_dataset_builder, tuple(PredictionTiming),
        (TendencyUnit("all", MEMBER_TYPES, ProbabilityOutput(TOP3_PROBABILITY)),)),
    TendencySource.FAVORITES_OUT: TendencySpec(
        "人気馬が4着以下", False, favorites_dataset_builder, tuple(FAVORITE_TIMINGS),
        _segment_units(FAVORITE_SEGMENTS, FAVORITE_OUT_PROBABILITY)),
    # 穴馬の予想の木曜のモデルは、利用者が人気を馬名で渡す前提なので、ここでは前日・当日だけ使う。
    TendencySource.LONGSHOTS_IN: TendencySpec(
        "穴馬が3着以内", False, longshots_dataset_builder, _WITH_ODDS,
        _segment_units(LONGSHOT_SEGMENTS, LONGSHOT_TOP3_PROBABILITY)),
    TendencySource.UPSET_LEVEL: TendencySpec(
        "レースの荒れ具合", True, upset_dataset_builder, tuple(PredictionTiming),
        tuple(TendencyUnit(bet.key, CLASS_MEMBER_TYPES, UpsetOutput(bet.key), label=bet.column_name) for bet in BetType)),
}
