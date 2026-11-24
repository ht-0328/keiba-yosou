"""組の表の全部の行に、当たる確率を付ける。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.ml_model import EnsembleModel, ProbabilityModel

from ..dataset import ModelDataFactory
from ..dataset.column_names import PROBABILITY

#: 1回に予測する行の数。3連単は1年で数百万行あるので、区切って予測してメモリを抑える。
_CHUNK_ROWS = 500_000


class TablePrediction:
    """1つの券種の学習済みモデル（LightGBM と CatBoost）で、組の表の行ごとの当たる確率を出す。

    戻り値の列は ``probability``（2つの平均）と、モデルごとの ``probability_lightgbm``・``probability_catboost``。
    行の並びと index は渡した表と同じ。
    """

    def __init__(self, ticket_type: TicketType, members: Sequence[ProbabilityModel]) -> None:
        self._factory = ModelDataFactory(ticket_type)
        self._ensemble = EnsembleModel(members)

    @property
    def columns(self) -> list[str]:
        """戻り値の列の名前。"""
        return [PROBABILITY, *(self._member_column(member.name) for member in self._ensemble.members)]

    def probabilities(self, table: pd.DataFrame) -> pd.DataFrame:
        if table.empty:
            return pd.DataFrame(columns=self.columns, index=table.index, dtype=float)
        starts = range(0, len(table), _CHUNK_ROWS)
        return pd.concat([self._chunk(table.iloc[start:start + _CHUNK_ROWS]) for start in starts])

    def _chunk(self, rows: pd.DataFrame) -> pd.DataFrame:
        by_member = self._ensemble.predict_members(self._factory.prediction(rows))
        columns = {self._member_column(name): values for name, values in by_member.items()}
        return pd.DataFrame({PROBABILITY: self._ensemble.combine(by_member), **columns}, index=rows.index)

    def _member_column(self, member_name: str) -> str:
        return f"{PROBABILITY}_{member_name.lower()}"
