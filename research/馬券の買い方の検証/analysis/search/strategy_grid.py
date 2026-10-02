"""格子から戦略の並びを作る。"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import upset_column
from ..participation import RacePattern
from ..ticket import TicketPlan, upset_bet_of
from .strategy import Strategy
from .threshold_grid import DANGER_THRESHOLDS, FORM_THRESHOLDS, TOP_KS, UPSET_TOP_SHARES


class StrategyGrid:
    """参加パターン × しきい値の格子 × 買い方 から戦略を作る。パターンが使わない軸は回さない。

    荒れ度の線は「上位 x%」で指定し、``strategies`` に渡した探索期間のレースで、広めの買い方の券種に対応する
    「中荒れ以上の確率」の分位から確率に直す。直した確率は戦略に持たせ、確認期間でもそのまま使う。
    """

    def __init__(self, patterns: Sequence[RacePattern], wide_plans: Sequence[TicketPlan], narrow_plans: Sequence[TicketPlan],
                 upset_shares: Sequence[float] = UPSET_TOP_SHARES, form_thresholds: Sequence[float] = FORM_THRESHOLDS,
                 danger_thresholds: Sequence[float] = DANGER_THRESHOLDS, top_ks: Sequence[int] = TOP_KS) -> None:
        self._patterns = tuple(patterns)
        self._wide_plans = tuple(wide_plans)
        self._narrow_plans = tuple(narrow_plans)
        self._upset_shares = tuple(upset_shares)
        self._form_thresholds = tuple(form_thresholds)
        self._danger_thresholds = tuple(danger_thresholds)
        self._top_ks = tuple(top_ks)

    def strategies(self, search_races: pd.DataFrame) -> list[Strategy]:
        out: list[Strategy] = []
        for pattern in self._patterns:
            out += self._for_pattern(pattern, search_races)
        return out

    def _for_pattern(self, pattern: RacePattern, races: pd.DataFrame) -> list[Strategy]:
        needs = pattern.needs
        axes = itertools.product(
            [plan.name for plan in self._wide_plans] if needs.wide else [None],
            [plan.name for plan in self._narrow_plans] if needs.narrow else [None],
            self._upset_shares if needs.upset else (None,),
            self._form_thresholds if needs.form else (None,),
            self._danger_thresholds if needs.danger else (None,),
            self._top_ks if needs.top_k else (None,),
        )
        return [self._strategy(pattern, races, *axis) for axis in axes]

    def _strategy(self, pattern: RacePattern, races: pd.DataFrame, wide: str | None, narrow: str | None,
                  share: float | None, form: float | None, danger: float | None, top_k: int | None) -> Strategy:
        return Strategy(pattern.key, wide, narrow, share, self._threshold(races, wide, share), form, danger, top_k)

    def _threshold(self, races: pd.DataFrame, wide_name: str | None, share: float | None) -> float | None:
        """上位 x% に当たる「中荒れ以上の確率」（広めの買い方の券種で決める）。"""
        if share is None:
            return None
        bet = self._wide_bet(wide_name)
        return float(races[upset_column(bet)].quantile(1.0 - share))

    def _wide_bet(self, wide_name: str | None) -> BetType:
        if wide_name is None:
            return BetType.WIN
        return upset_bet_of(next(plan for plan in self._wide_plans if plan.name == wide_name).ticket_type)
