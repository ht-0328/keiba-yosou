"""1レースを予測するときの、予測用データの入れ物。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import duckdb

from yosou.shared.dataset import OddsInput, OddsResolver, PopularityApplier, PredictionData
from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import AnnouncedOddsRepository

from ..dataset import horse_dataset_builder, race_dataset_builder
from ..tendency import TendencySource


@dataclass(frozen=True)
class RaceInputs:
    """1レースの予測用データ（1頭ごと・1レースごと・その時点で予測を出す既存の予想ごと）。

    ``read`` で、開いた元DB から作る。オッズは、利用者が渡したもの → 締め切り前のオッズ → 元DB の単勝オッズの順に決め、
    人気はオッズの小さい順に決める（人気馬・穴馬の予想が、行を選ぶのに使う）。
    """

    horses: PredictionData
    races: PredictionData
    tendency: Mapping[TendencySource, PredictionData]

    @classmethod
    def read(cls, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
             given_odds: OddsInput | None = None) -> RaceInputs:
        """前日・当日の既存の予想は、オッズから見た確率を出発点にするので、オッズが決められなければ ``ValueError``。"""
        announced = AnnouncedOddsRepository(con)
        odds = OddsResolver(announced).resolve(race_id, given_odds)
        popularity = PopularityApplier(announced).resolve(race_id, None, odds)
        horses = horse_dataset_builder(con).build_prediction_data(race_id, timing, odds=odds)
        races = race_dataset_builder(con).build_prediction_data(race_id, timing, odds=odds)
        tendency = {source: source.prediction_data(con, race_id, timing, popularity, odds)
                    for source in TendencySource if source.predicts_at(timing)}
        return cls(horses, races, tendency)
