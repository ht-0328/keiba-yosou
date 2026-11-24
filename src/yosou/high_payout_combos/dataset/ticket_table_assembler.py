"""1つの券種の組の表を組み立てる。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import horse_columns

from ..feature import (
    CATALOGS,
    LOG_HV,
    ComboSummaryFeatures,
    CrossMarketFeatures,
    HarvilleFeatures,
    OwnMarketFeatures,
    PositionHorseFeatures,
    RaceFeatures,
    RegionFeatures,
)
from ..feature.column_names import LOG_Q
from .column_names import BASELINE, COMBO, ODDS, RACE_ID, TICKET_TYPE
from .combo_member_lookup import ComboMemberLookup
from .payout_band import PayoutBand
from .table_columns import built_columns

#: 出発点にする市場の確率の下限と上限（ロジットが −∞・+∞ にならないように）。
_MIN_BASE_PROBABILITY, _MAX_BASE_PROBABILITY = 1e-9, 0.999
#: 材料と出発点を持つ型（3連単は1年で数百万行になるので、小さい型にする）。
_FEATURE_TYPE = np.float32


class TicketTableAssembler:
    """1回ぶん（1か月か1レース）の市場の表・馬ごとの材料・レースごとの表から、1つの券種の組の表を組み立てる。

    対象の行（オッズが学ぶ下限以上・上限未満で、組の馬が全部馬ごとの材料の表にいる組）だけを残し、材料のまとまり
    （A〜F。``feature`` の各クラス）を順に付ける。出発点（``baseline``）は logit(clip(q, 1e-9, 0.999))。
    列は ``table_columns.built_columns``（レースID・券種・組番・馬番・オッズ・出発点・材料）。対象の行が無ければ、列だけの空の表。
    """

    def __init__(self, markets: Mapping[TicketType, pd.DataFrame], materials: pd.DataFrame, races: pd.DataFrame) -> None:
        self._markets = markets
        self._materials = materials
        self._races = races
        self._lookup = ComboMemberLookup(materials)
        self._cross = CrossMarketFeatures(markets)

    def table(self, band: PayoutBand) -> pd.DataFrame:
        ticket_type = band.ticket_type
        market = self._markets[ticket_type]
        in_band = market[band.is_learnable(market[ODDS])]
        slots = self._lookup.slots(in_band, ticket_type.spec.horse_count)
        has_all_horses = (slots >= 0).all(axis=1)
        rows = in_band[has_all_horses].reset_index(drop=True)
        if rows.empty:
            return pd.DataFrame(columns=built_columns(ticket_type))
        members = self._lookup.members(slots[has_all_horses], ticket_type.spec.is_ordered)
        harville = HarvilleFeatures().of(ticket_type, rows, members, self._materials)
        features = pd.concat([
            OwnMarketFeatures().of(rows), self._cross.of(ticket_type, rows), harville,
            PositionHorseFeatures().of(members, rows.index), ComboSummaryFeatures().of(members, rows.index),
            RaceFeatures().of(rows, self._races, members),
            RegionFeatures().of(market, band.learn_from, rows, harville[LOG_HV]),
        ], axis=1)
        return self._assembled(ticket_type, rows, features)

    def _assembled(self, ticket_type: TicketType, rows: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """ID・オッズ・出発点・材料を、決まった列の並びと型で1つの表にする。"""
        names = horse_columns(ticket_type.spec.horse_count)
        ids = rows[[RACE_ID, COMBO, ODDS]].assign(**{name: rows[name].astype(np.int8) for name in names})
        ids[TICKET_TYPE] = ticket_type.label
        ids[BASELINE] = self._baseline(rows[LOG_Q])
        table = pd.concat([ids, features[list(CATALOGS[ticket_type].names)].astype(_FEATURE_TYPE)], axis=1)
        return table[built_columns(ticket_type)]

    def _baseline(self, log_q: pd.Series) -> pd.Series:
        probability = np.exp(log_q.astype(float)).clip(_MIN_BASE_PROBABILITY, _MAX_BASE_PROBABILITY)
        return np.log(probability / (1.0 - probability))
