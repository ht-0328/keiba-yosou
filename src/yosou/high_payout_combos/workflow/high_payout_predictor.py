"""1レースの、高配当の組が当たる確率を出す。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Self

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import horse_columns
from yosou.shared.ml_model import ProbabilityModel

from ..dataset import DEFAULT_BANDS, ComboTableBuilder, PayoutBand
from ..dataset.column_names import COMBO, HORSES, ODDS, PROBABILITY, RACE_ID, TICKET_TYPE, VALUE
from ..feature import TICKET_TYPES
from ..repository import TicketModelRepository
from .table_prediction import TablePrediction

#: 予測の結果の列。
PREDICTION_COLUMNS: tuple[str, ...] = (RACE_ID, TICKET_TYPE, COMBO, HORSES, ODDS, PROBABILITY, VALUE)


class HighPayoutPredictor:
    """本番の予測の入口。1レースの馬ごとの表と5券種のオッズの板から、対象の組（オッズが学ぶ下限以上・上限未満）の当たる確率を出す。

    - ``horses``: その1レースの馬ごとの表（1頭1行。列は ``repository/horse_table_columns.py`` の ``MATERIAL_COLUMNS``）。
    - ``boards``: 券種 → オッズの板（列 ``race_id``・``combo``・``odds``。ワイドは最低オッズ）。締め切り前のいちばん新しい断面を渡す。

    戻り値は1行 = 1つの組。列は ``race_id``・``ticket_type``（``TicketType`` の label）・``combo``（組番）・``horses``（馬番の並びのタプル）・
    ``odds``・``probability``（LightGBM と CatBoost の平均）・``value``（確率 × オッズ）。買う組を選ぶのは ``HighPayoutRule``。

    モデルの無い券種は扱わない。板が足りない券種（その券種の板が無い・3連単の板が無い・ほかの券種の市場の材料に要る板が無い）は、
    誤りにせず、その券種の行を出さない（どの券種も出せなければ、列だけの空の表）。
    """

    def __init__(self, members: Mapping[TicketType, Sequence[ProbabilityModel]],
                 bands: Mapping[TicketType, PayoutBand] = DEFAULT_BANDS) -> None:
        """``members`` は券種 → 学習済みのモデル（LightGBM・CatBoost）、``bands`` は券種ごとの帯。"""
        self._predictions = {ticket_type: TablePrediction(ticket_type, models) for ticket_type, models in members.items()}
        self._builder = ComboTableBuilder(bands)

    @classmethod
    def load(cls, models_folder: Path, bands: Mapping[TicketType, PayoutBand] = DEFAULT_BANDS) -> Self:
        """``models_folder``（``train`` が書いた ``models/``）から、保存してある券種のモデルを読む。"""
        repository = TicketModelRepository(models_folder)
        available = [ticket_type for ticket_type in TICKET_TYPES if repository.has(ticket_type)]
        return cls({ticket_type: repository.load(ticket_type) for ticket_type in available}, bands)

    @property
    def ticket_types(self) -> tuple[TicketType, ...]:
        """予測できる券種（モデルのある券種）。"""
        return tuple(self._predictions)

    def predict(self, horses: pd.DataFrame, boards: Mapping[TicketType, pd.DataFrame]) -> pd.DataFrame:
        tables = self._builder.build(horses, boards, self.ticket_types)
        predicted = [self._predicted(ticket_type, table) for ticket_type, table in tables.items() if not table.empty]
        if not predicted:
            return pd.DataFrame(columns=list(PREDICTION_COLUMNS))
        return pd.concat(predicted, ignore_index=True)

    def _predicted(self, ticket_type: TicketType, table: pd.DataFrame) -> pd.DataFrame:
        probability = self._predictions[ticket_type].probabilities(table)[PROBABILITY]
        numbers = table[horse_columns(ticket_type.spec.horse_count)].to_numpy(dtype=int).tolist()
        return pd.DataFrame({
            RACE_ID: table[RACE_ID], TICKET_TYPE: table[TICKET_TYPE], COMBO: table[COMBO],
            HORSES: pd.Series([tuple(row) for row in numbers], index=table.index, dtype=object),
            ODDS: table[ODDS], PROBABILITY: probability, VALUE: probability * table[ODDS],
        })[list(PREDICTION_COLUMNS)]
