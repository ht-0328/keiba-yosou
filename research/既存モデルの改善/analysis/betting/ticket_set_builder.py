"""レース × 券種 ごとに、期待値の低い買い目を切り、点数を絞り、賭け金と券種全体の期待値・合成オッズを付ける。"""

from __future__ import annotations

from collections.abc import Collection, Sequence

import numpy as np
import pandas as pd

from ..ticket_combos import TICKET_SPECS, TicketSpec
from .candidate_columns import GROUP, ODDS, PRICE, PROBABILITY, RACE, RETURN, SET_ODDS, SET_STAKE, SET_VALUE, STAKE, TICKET, VALUE
from .payout_table import PAYOUT
from .stake_allocator import StakeAllocator

#: 買い目1つの期待値の下限（これより低い買い目は切る）。
MIN_VALUE = 1.0


class TicketSetBuilder:
    """買い目の候補（確率を補正したもの。払戻の列も持つ）から、レース × 券種 ごとの買い目の組を作る。

    1. 期待値が ``MIN_VALUE`` より低い買い目を切る。
    2. 組み合わせの種類ごとの上限（人気-人気は1点）と、券種の点数の上限（荒れそうなレースは広め）まで、期待値の高い順に残す。
    3. 賭け金を割り振る（``StakeAllocator``。3連単 100円・3連複 300円・ほかは払戻均等。トリガミになる買い目は外す）。
    4. 券種全体の期待値（Σ 当たる確率 × 見込みの倍率 × 賭け金 ÷ 券種の賭け金）と合成オッズ、払戻（円）を付ける。
    どの券種を買うかは、ここでは決めない（``BettingPlan`` が券種全体の期待値で決める）。
    """

    def __init__(self, specs: Sequence[TicketSpec] = TICKET_SPECS) -> None:
        self._specs = {spec.ticket.label: spec for spec in specs}
        self._allocator = StakeAllocator()

    def build(self, candidates: pd.DataFrame, upset_races: Collection[str]) -> pd.DataFrame:
        upset = set(upset_races)
        kept = candidates[candidates[VALUE] >= MIN_VALUE]
        sets = [self._set(self._specs[ticket], part, race in upset) for (race, ticket), part in kept.groupby([RACE, TICKET], sort=False)]
        frames = [frame for frame in sets if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else candidates.iloc[0:0].assign(
            **{STAKE: [], SET_STAKE: [], SET_VALUE: [], SET_ODDS: [], RETURN: []})

    def _set(self, spec: TicketSpec, part: pd.DataFrame, upset: bool) -> pd.DataFrame:
        ranked = part.sort_values(VALUE, ascending=False, kind="stable")
        within = ranked.groupby(GROUP).cumcount() < ranked[GROUP].map(spec.group_limits).fillna(np.inf)
        chosen = ranked[within].head(spec.points_for(upset))
        stakes = self._allocator.allocate(spec, chosen[ODDS].to_numpy(dtype="float64"))
        chosen = chosen.assign(**{STAKE: stakes})[stakes > 0]
        if chosen.empty:
            return chosen
        total = float(chosen[STAKE].sum())
        return chosen.assign(**{
            SET_STAKE: total,
            SET_VALUE: float((chosen[PROBABILITY] * chosen[PRICE] * chosen[STAKE]).sum()) / total,
            SET_ODDS: float((chosen[STAKE] * chosen[ODDS]).min()) / total,
            RETURN: chosen[PAYOUT] * chosen[STAKE] / 100.0,
        })
