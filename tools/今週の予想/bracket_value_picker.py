"""印を付けた表と、馬連・3連単・枠連のオッズの板と枠番から、枠連の組の期待値で選ぶ買い目を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import BRACKET, TicketType
from yosou.shared.combo_value import (
    HARVILLE,
    MARKET,
    BracketBlendWeights,
    ComboBlendFeatures,
    HorseStrength,
    PoolFolding,
    TrifectaSources,
    split_combo,
)
from yosou.shared.win_value import HIGH

from 今週の予想.combo_race_traits import ComboRaceTraits
from 今週の予想.combo_value_rule import HIGH_RACES, HIGH_TOP_COMBOS, TOP_COMBOS, ComboValueRule
from 今週の予想.filter_columns import AGREEMENT, POOL_BACKED
from 今週の予想.forecast_columns import HORSE_NO, MARK, WIN_VALUE_BAND
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.mark_tickets import COLUMNS, RULE, VALUE

#: レースから写す列（無ければ偽か欠損）。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", WIN_VALUE_BAND, AGREEMENT, POOL_BACKED)
#: 対数を取る前の下限（本番の ``ComboBlendFeatures`` と同じ）。
_FLOOR = 1e-9


class BracketValuePicker:
    """印を付けた表（1行 = 1頭。何レースぶんでもよい）と、馬連・3連単・枠連のオッズの板（列 ``race_id``・``combo``・``odds``）と、
    枠番（``FrameRepository`` の列 ``race_id``・``horse_no``・``frame``）から、枠連の組の期待値の買い目（1行 = 1点。列は ``MarkTickets`` の
    ``COLUMNS``。組番は枠の番号を1桁ずつ並べた2文字）を作る（研究「レースの種類ごとの買い方」の docs/04 の 3）。

    1. 馬連の全部の組に、本番の部品（``ComboBlendFeatures``）で馬連の市場・3連単から見た市場・モデルの Harville を付ける。
    2. その3つを、2頭の枠の組（小さい枠が先。同じ枠どうしを含む）ごとに足す。
    3. 枠連の市場（枠連のオッズの逆数をレースで合計 1）と合わせ、重み（``BracketBlendWeights``）で組の確率にし、期待値 = 確率 × 枠連のオッズ。
    4. ルール（``ComboValueRule``。券種は ``BRACKET``）の線・上限・対象・レースの条件・点数で選ぶ。
    重みか板か枠番が無ければ 0点。
    """

    def __init__(self, rule: ComboValueRule, weights: BracketBlendWeights | None) -> None:
        self._rule = rule
        self._weights = weights
        self._features = ComboBlendFeatures()
        self._folding = PoolFolding()

    @property
    def ready(self) -> bool:
        """重みがあって、買い目を作れるか。"""
        return self._weights is not None

    def pick(self, marked: pd.DataFrame, boards: dict[TicketType, pd.DataFrame], bracket_board: pd.DataFrame,
             frames: pd.DataFrame) -> pd.DataFrame:
        empty = pd.DataFrame(columns=list(COLUMNS))
        quinella, trifecta = boards.get(TicketType.QUINELLA), boards.get(TicketType.TRIFECTA)
        if (self._weights is None or marked.empty or any(board is None or board.empty for board in (quinella, trifecta))
                or bracket_board.empty or frames.empty):
            return empty
        valued = self._valued(marked, quinella, trifecta, bracket_board, frames)
        chosen = valued[(valued[VALUE] >= self._rule.value_line) & (valued["odds"] <= self._rule.odds_cap)]
        chosen = chosen.merge(self._races(marked, frames), on="race_id", how="inner")
        if self._rule.scope in (HIGH_RACES, HIGH_TOP_COMBOS):
            chosen = chosen[chosen[WIN_VALUE_BAND] == HIGH]
        if self._rule.scope in (TOP_COMBOS, HIGH_TOP_COMBOS):
            chosen = chosen[(chosen["f1"] == chosen["top_frame"]) | (chosen["f2"] == chosen["top_frame"])]
        for condition in self._rule.race_conditions:
            chosen = chosen[condition.passes(chosen)]
        if self._rule.max_points:
            chosen = chosen[chosen.groupby("race_id")[VALUE].rank(ascending=False, method="first") <= self._rule.max_points]
        if chosen.empty:
            return empty
        return chosen.assign(**{RULE: self._rule.label, "ticket_type": BRACKET.label, "stake_units": self._rule.stake_units})[list(COLUMNS)]

    def _valued(self, marked: pd.DataFrame, quinella: pd.DataFrame, trifecta: pd.DataFrame, bracket_board: pd.DataFrame,
                frames: pd.DataFrame) -> pd.DataFrame:
        """枠の組ごとの、組の確率と期待値（列 ``race_id``・``combo``・``f1``・``f2``・``odds``・``value``）。"""
        strength = HorseStrength().of(marked)
        sources = TrifectaSources().of(split_combo(trifecta, 3), strength)
        folded = self._folding.fold(TicketType.QUINELLA, sources, [MARKET, HARVILLE])
        pairs = self._features.build(TicketType.QUINELLA, quinella, folded, strength)
        frame_of = frames.assign(race_id=frames["race_id"].astype(str)).set_index(["race_id", "horse_no"])["frame"]
        one = frame_of.reindex(pd.MultiIndex.from_arrays([pairs["race_id"], pairs["h1"].astype(int)])).to_numpy()
        two = frame_of.reindex(pd.MultiIndex.from_arrays([pairs["race_id"], pairs["h2"].astype(int)])).to_numpy()
        pairs = pairs.assign(f1=np.fmin(one, two), f2=np.fmax(one, two), q=np.exp(pairs["log_own"]), t=np.exp(pairs["log_trifecta"]),
                             hv=np.exp(pairs["log_harville"])).dropna(subset=["f1", "f2"])
        grouped = pairs.groupby(["race_id", "f1", "f2"], as_index=False)[["q", "t", "hv"]].sum()
        grouped["combo"] = grouped["f1"].astype(int).astype(str) + grouped["f2"].astype(int).astype(str)
        board = bracket_board.assign(race_id=bracket_board["race_id"].astype(str), combo=bracket_board["combo"].astype(str))
        table = grouped.merge(board[board["odds"] > 0][["race_id", "combo", "odds"]], on=["race_id", "combo"], how="inner")
        inverse = 1.0 / table["odds"]
        own = inverse / inverse.groupby(table["race_id"]).transform("sum")
        logs = np.column_stack([np.log(column.clip(lower=_FLOOR)) for column in (own, table["q"], table["t"], table["hv"])])
        score = pd.Series(logs @ np.asarray(self._weights.values()), index=table.index)
        exponent = np.exp(score - score.groupby(table["race_id"]).transform("max"))
        probability = exponent / exponent.groupby(table["race_id"]).transform("sum")
        return table.assign(**{VALUE: probability * table["odds"]})

    def _races(self, marked: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レースの、買い目に写す列と ◎ の枠（``top_frame``。◎ がいなければ欠損）と、レースの中身（``ComboRaceTraits``）。"""
        first = marked.groupby("race_id", sort=False).first().reset_index()
        races = pd.DataFrame({name: (first[name] if name in first.columns else np.nan) for name in _RACE_COLUMNS}, index=first.index)
        races["race_id"] = races["race_id"].astype(str)
        for flag in (AGREEMENT, POOL_BACKED):
            races[flag] = races[flag].fillna(False).astype(bool)
        tops = marked[marked[MARK] == TOP_MARK] if MARK in marked.columns else marked.iloc[0:0]
        frame_of = frames.assign(race_id=frames["race_id"].astype(str)).set_index(["race_id", "horse_no"])["frame"]
        top_frames = frame_of.reindex(pd.MultiIndex.from_arrays([tops["race_id"].astype(str), tops[HORSE_NO].astype(int)])).to_numpy()
        races["top_frame"] = races["race_id"].map(dict(zip(tops["race_id"].astype(str), top_frames)))
        return races.merge(ComboRaceTraits().of(marked), on="race_id", how="left")
