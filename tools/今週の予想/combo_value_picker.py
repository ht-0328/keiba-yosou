"""印を付けた表とオッズの板から、組の期待値で選ぶ買い目を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import (
    HARVILLE,
    MARKET,
    ComboBlend,
    ComboBlendFeatures,
    ComboBlendWeights,
    HorseStrength,
    PoolFolding,
    TrifectaSources,
    split_combo,
)
from yosou.shared.combo_value.combo_blend import VALUE
from yosou.shared.win_value import HIGH

from 今週の予想.combo_value_rule import HIGH_RACES, ComboValueRule
from 今週の予想.filter_columns import AGREEMENT, POOL_BACKED
from 今週の予想.forecast_columns import EXPECTATION
from 今週の予想.mark_tickets import COLUMNS, RULE

#: レースから写す列（無ければ偽か欠損）。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", EXPECTATION, AGREEMENT, POOL_BACKED)


class ComboValuePicker:
    """印を付けた表（1行 = 1頭。何レースぶんでもよい）と、券種ごとのオッズの板（列 ``race_id``・``combo``・``odds``）から、
    ``ComboValueRule`` の買い目（1行 = 1点）を作る。列は ``MarkTickets`` の ``COLUMNS``（オッズは、ほかの買い目と同じく呼ぶ側が付ける）。

    組の確率は、3連単の板から市場とモデルの Harville を作って券種の組に足し合わせ（``TrifectaSources``・``PoolFolding``）、
    その券種の板と馬ごとの比と合わせて、重み（``weights``）で1つにする（``ComboBlendFeatures``・``ComboBlend``）。
    3連単の板か、その券種の板か、重みが無い券種は 0点。期待度「高」のレースだけのルールは、ほかのレースの組を落とす。
    """

    def __init__(self, rules: tuple[ComboValueRule, ...], weights: dict[TicketType, ComboBlendWeights]) -> None:
        self._rules = rules
        self._weights = weights
        self._features = ComboBlendFeatures()
        self._blend = ComboBlend()
        self._folding = PoolFolding()

    def needed(self) -> tuple[TicketType, ...]:
        """読むオッズの板の券種（ルールの券種と、組の確率のもとになる3連単）。重みの無い券種は読まない。"""
        wanted = [rule.ticket_type for rule in self._rules if rule.ticket_type in self._weights]
        return tuple(dict.fromkeys([*wanted, TicketType.TRIFECTA])) if wanted else ()

    def pick(self, marked: pd.DataFrame, boards: dict[TicketType, pd.DataFrame]) -> pd.DataFrame:
        trifecta = boards.get(TicketType.TRIFECTA)
        if marked.empty or trifecta is None or trifecta.empty:
            return pd.DataFrame(columns=list(COLUMNS))
        strength = HorseStrength().of(marked)
        sources = TrifectaSources().of(split_combo(trifecta, 3), strength)
        races = self._races(marked)
        parts = [self._rule_tickets(rule, boards.get(rule.ticket_type), sources, strength, races) for rule in self._rules]
        parts = [part for part in parts if not part.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(COLUMNS))

    def _rule_tickets(self, rule: ComboValueRule, board: pd.DataFrame | None, sources: pd.DataFrame, strength: pd.DataFrame,
                      races: pd.DataFrame) -> pd.DataFrame:
        weights = self._weights.get(rule.ticket_type)
        if weights is None or board is None or board.empty:
            return pd.DataFrame()
        folded = self._folding.fold(rule.ticket_type, sources, [MARKET, HARVILLE])
        features = self._features.build(rule.ticket_type, board, folded, strength)
        valued = self._blend.of(rule.ticket_type, features, weights)
        chosen = valued[(valued[VALUE] >= rule.value_line) & (valued["odds"] <= rule.odds_cap)]
        chosen = chosen.merge(races, on="race_id", how="inner")
        if rule.scope == HIGH_RACES:
            chosen = chosen[chosen[EXPECTATION] == HIGH]
        return chosen.assign(**{RULE: rule.label, "ticket_type": rule.ticket_type.label, "stake_units": rule.stake_units})[list(COLUMNS)]

    def _races(self, marked: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レースの、買い目に写す列。"""
        first = marked.groupby("race_id", sort=False).first().reset_index()
        columns = {name: (first[name] if name in first.columns else np.nan) for name in _RACE_COLUMNS}
        races = pd.DataFrame(columns, index=first.index)
        races["race_id"] = races["race_id"].astype(str)
        for flag in (AGREEMENT, POOL_BACKED):
            races[flag] = races[flag].fillna(False).astype(bool)
        return races
