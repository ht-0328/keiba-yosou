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
from yosou.shared.combo_value.combo_blend import PROBABILITY, VALUE
from yosou.shared.win_value import HIGH

from 今週の予想.combo_race_traits import ComboRaceTraits
from 今週の予想.combo_value_rule import HIGH_RACES, HIGH_TOP_COMBOS, TOP_COMBOS, ComboValueRule
from 今週の予想.filter_columns import AGREEMENT, POOL_BACKED
from 今週の予想.forecast_columns import HORSE_NO, MARK, WIN_VALUE_BAND
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.mark_tickets import COLUMNS, RULE

#: レースから写す列（無ければ偽か欠損）。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", WIN_VALUE_BAND, AGREEMENT, POOL_BACKED)
#: ◎ の馬番の列（``TOP_COMBOS`` のルールに使う。買い目には写さない）。
_TOP = "top_horse"


class ComboValuePicker:
    """印を付けた表（1行 = 1頭。何レースぶんでもよい）と、券種ごとのオッズの板（列 ``race_id``・``combo``・``odds``）から、
    ``ComboValueRule`` の買い目（1行 = 1点）を作る。列は ``MarkTickets`` の ``COLUMNS``（オッズは、ほかの買い目と同じく呼ぶ側が付ける）。

    組の確率は、3連単の板から市場とモデルの Harville を作って券種の組に足し合わせ（``TrifectaSources``・``PoolFolding``）、
    その券種の板と馬ごとの比と合わせて、重み（``weights``）で1つにする（``ComboBlendFeatures``・``ComboBlend``）。
    3連単の板か、その券種の板か、重みが無い券種は 0点。◎の期待値 1.00 以上のレースだけのルールは、ほかのレースの組を落とし、
    ◎ を含む組だけのルールは ◎ を含まない組（馬単・3連単は ◎ が1着でない組）を落とす。レースの条件（``race_conditions``）のあるルールは、
    条件のどれかに合わないレース（中身は ``ComboRaceTraits``）の組を落とす。1レースの点数の上限があれば、組の期待値の高い順に残す。

    2段に分かれている。``candidates`` は印と消に依らない段（確率と板から、線以上・上限以下の組を出す）、``select`` は印と消で決まる段
    （◎の期待値の帯・◎ を含む組・レースの条件・点数で絞る）。``pick`` はその2段を続けて行う。消の決め方を替えて比べるときは、
    ``candidates`` を1回だけ作って ``select`` を繰り返せる。
    """

    def __init__(self, rules: tuple[ComboValueRule, ...], weights: dict[TicketType, ComboBlendWeights]) -> None:
        self._rules = rules
        self._weights = weights
        self._features = ComboBlendFeatures()
        self._blend = ComboBlend()
        self._folding = PoolFolding()

    def with_weights(self, weights: dict[TicketType, ComboBlendWeights]) -> ComboValuePicker:
        """同じルールで、重みを直前1年で推定し直す券種（ルールの ``rolling``）の重みだけを ``weights`` に差し替えた部品。"""
        rolling = {rule.ticket_type for rule in self._rules if rule.rolling}
        return ComboValuePicker(self._rules, {**self._weights, **{key: value for key, value in weights.items() if key in rolling}})

    @property
    def rules(self) -> tuple[ComboValueRule, ...]:
        """買い目のルール（``candidates`` の並びと同じ順）。"""
        return self._rules

    def needed(self) -> tuple[TicketType, ...]:
        """読むオッズの板の券種（ルールの券種と、組の確率のもとになる3連単）。重みの無い券種は読まない。"""
        wanted = [rule.ticket_type for rule in self._rules if rule.ticket_type in self._weights]
        return tuple(dict.fromkeys([*wanted, TicketType.TRIFECTA])) if wanted else ()

    def pick(self, marked: pd.DataFrame, boards: dict[TicketType, pd.DataFrame]) -> pd.DataFrame:
        candidates = self.candidates(marked, boards)
        if not candidates:
            return pd.DataFrame(columns=list(COLUMNS))
        races = self.races(marked)
        parts = [self.select(rule, candidate, races) for rule, candidate in zip(self._rules, candidates, strict=True)]
        parts = [part for part in parts if not part.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(COLUMNS))

    def candidates(self, horses: pd.DataFrame, boards: dict[TicketType, pd.DataFrame]) -> list[pd.DataFrame]:
        """印と消に依らない段。ルールごと（``rules`` の順）に、組の期待値が線以上でオッズが上限以下の組
        （列 ``race_id``・``combo``・``h1``〜・``odds``・``value``）。``horses`` は1行 = 1頭の表（確率と市場の見立ての列だけ使う。印の列は見ない）。
        3連単の板が無いか表が空なら空の一覧。重みや板の無いルールは空の表。"""
        trifecta = boards.get(TicketType.TRIFECTA)
        if horses.empty or trifecta is None or trifecta.empty:
            return []
        strength = HorseStrength().of(horses)
        sources = TrifectaSources().of(split_combo(trifecta, 3), strength)
        return [self._candidates_of(rule, boards.get(rule.ticket_type), sources, strength) for rule in self._rules]

    def select(self, rule: ComboValueRule, candidates: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """印と消で決まる段。``candidates``（``candidates`` の1つ）を、``races``（``races`` の戻り値）で絞って買い目の形にする。
        ◎の期待値 1.00 以上のレースだけのルール・◎ を含む組だけのルール・レースの条件・1レースの点数の上限を当てる。"""
        if candidates.empty:
            return pd.DataFrame()
        chosen = candidates.merge(races, on="race_id", how="inner")
        if rule.scope in (HIGH_RACES, HIGH_TOP_COMBOS):
            chosen = chosen[chosen[WIN_VALUE_BAND] == HIGH]
        if rule.scope in (TOP_COMBOS, HIGH_TOP_COMBOS):
            chosen = chosen[self._has_top(rule.ticket_type, chosen)]
        for condition in rule.race_conditions:
            chosen = chosen[condition.passes(chosen)]
        if rule.max_points:
            chosen = chosen[chosen.groupby("race_id")[VALUE].rank(ascending=False, method="first") <= rule.max_points]
        return chosen.assign(**{RULE: rule.label, "ticket_type": rule.ticket_type.label, "stake_units": rule.stake_units})[list(COLUMNS)]

    def races(self, marked: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レースの、買い目に写す列と ◎ の馬番（印が無ければ欠損）と、レースの中身（``ComboRaceTraits``）。``select`` に渡す。"""
        first = marked.groupby("race_id", sort=False).first().reset_index()
        columns = {name: (first[name] if name in first.columns else np.nan) for name in _RACE_COLUMNS}
        races = pd.DataFrame(columns, index=first.index)
        races["race_id"] = races["race_id"].astype(str)
        tops = marked[marked[MARK] == TOP_MARK] if MARK in marked.columns else marked.iloc[0:0]
        top_of = dict(zip(tops["race_id"].astype(str), tops[HORSE_NO].astype(int)))
        races[_TOP] = races["race_id"].map(top_of)
        for flag in (AGREEMENT, POOL_BACKED):
            races[flag] = races[flag].fillna(False).astype(bool)
        return races.merge(ComboRaceTraits().of(marked), on="race_id", how="left")

    def _candidates_of(self, rule: ComboValueRule, board: pd.DataFrame | None, sources: pd.DataFrame, strength: pd.DataFrame) -> pd.DataFrame:
        weights = self._weights.get(rule.ticket_type)
        if weights is None or board is None or board.empty:
            return pd.DataFrame()
        folded = self._folding.fold(rule.ticket_type, sources, [MARKET, HARVILLE])
        features = self._features.build(rule.ticket_type, board, folded, strength)
        valued = self._blend.of(rule.ticket_type, features, weights)
        return valued[(valued[VALUE] >= rule.value_line) & (valued["odds"] <= rule.odds_cap) & (valued[PROBABILITY] >= rule.min_probability)]

    def _has_top(self, ticket_type: TicketType, chosen: pd.DataFrame) -> pd.Series:
        """◎ を含む組か（着順を区別する券種は ◎ が1着の組か）。"""
        if ticket_type.spec.is_ordered:
            return chosen["h1"] == chosen[_TOP]
        names = ("h1", "h2", "h3")[:ticket_type.spec.horse_count]
        return chosen[list(names)].eq(chosen[_TOP], axis=0).any(axis=1)
