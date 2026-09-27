"""1レースを、保存した既存の予想のモデルで予測する（傾向の組）。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData

from ..feature import GroupForecast
from .tendency_model_store import TendencyModelStore
from .tendency_source import TendencySource
from .tendency_unit import TendencyUnit
from .unit_table_combiner import UnitTableCombiner


class TendencyForecaster:
    """既存の予想ごとの予測用データを、単位（区分・券種）ごとのモデルで予測し、傾向の組の予測にする（設計書 05 の図2）。

    予測用データに行の無い単位（例: そのレースに 4〜5番人気の区分の馬がいない）は、モデルを読まない。
    """

    def __init__(self, store: TendencyModelStore) -> None:
        self._store = store
        self._combiner = UnitTableCombiner()

    def predict(self, data: Mapping[TendencySource, PredictionData]) -> GroupForecast:
        """``data`` は 既存の予想 → そのレースの予測用データ（その時点で予測を出す既存の予想だけ）。"""
        horse_parts = [self._source(source, rows) for source, rows in data.items() if not source.spec.per_race]
        race_parts = [self._source(source, rows) for source, rows in data.items() if source.spec.per_race]
        return GroupForecast.joined(horse_parts, race_parts)

    def _source(self, source: TendencySource, data: PredictionData) -> pd.DataFrame:
        keys = [RACE_ID] if source.spec.per_race else [RACE_ID, HORSE_ID]
        parts = [self._unit(source, unit, data, keys) for unit in source.spec.units]
        return self._combiner.combine(parts, keys)

    def _unit(self, source: TendencySource, unit: TendencyUnit, data: PredictionData,
              keys: list[str]) -> pd.DataFrame | None:
        runners = unit.runners(data)
        if len(runners) == 0:
            return None
        members = self._store.load(source, unit, data.timing)
        return pd.concat([runners.ids[keys], unit.predict(members, runners)], axis=1)
