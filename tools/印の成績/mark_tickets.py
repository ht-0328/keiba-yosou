"""印を付けた表から、券種ごとの買い目を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboExpectedValue, HorseRatio

from 今週の予想.forecast_columns import (
    AXIS,
    EXPECTATION,
    HORSE_NO,
    MARK,
    MARKET_TOP3,
    MARKET_WIN,
    PLACE_VALUE,
    PROBABILITY,
    WIN_PROBABILITY,
)
from 今週の予想.mark_rule import TOP_MARK

from 印の成績.axis_ticket_rule import HORSE_AXIS, TOP_AXIS, AxisTicketRule
from 印の成績.ticket_rules import (
    BET_RULES,
    PLACE_LABEL,
    PLACE_MAX_POINTS,
    PLACE_STAKE_UNITS,
    PLACE_VALUE_LINE,
    TicketRule,
    combo_text,
)

#: 買い目の表の列。``rule`` は買い方の名前（表の行）、``ticket_type`` は券種の名前（払戻とオッズを読む表）、``value`` は組の期待値
#: （3連複・3連単だけ。ほかは欠損値）。
RULE, VALUE = "rule", "value"
COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", EXPECTATION, RULE, "ticket_type", "combo", "stake_units", VALUE)
#: レースから写す列。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", EXPECTATION)


class MarkTickets:
    """印を付けた表（``BacktestMarker.mark`` の戻り値。1行 = 1頭）から、印のルールの買い目（1行 = 1点）を作る
    （設計書「買うレースと買い目を決める」08 の 2。ルールは ``BET_RULES``）。

    - 印の位置で組む券種（``TicketRule``）: ルールの印の組み合わせを全部作る。
    - 軸から流す券種（``AxisTicketRule``。3連複・3連単）: 軸（◎軸は ◎、軸馬は列 ``axis`` の馬。無ければ ◎）から相手に流す。
      組の期待値（``ComboExpectedValue``。市場が見た組の確率 × 3頭の「モデル ÷ 市場」の比）を付け、線のあるルールは線以上の買い目だけにする。
    - 複勝: 複勝の期待値が線（1.25）以上の馬を、高い順に最大3点。
    列は ``COLUMNS``。
    """

    def __init__(self) -> None:
        self._ratio = HorseRatio()
        self._value = ComboExpectedValue()

    def build(self, marked: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict] = []
        for _, race in marked.groupby("race_id", sort=False):
            head = {column: race[column].iloc[0] for column in _RACE_COLUMNS}
            by_mark = self._horses_by_mark(race)
            axes = self._axes(race, by_mark)
            ratios = self._ratios(race)
            for rule in BET_RULES:
                combos = rule.combos(by_mark, axes)
                values = self._values(rule, combos, ratios)
                rows += [{**head, RULE: rule.label, "ticket_type": rule.ticket_type.label, "combo": combo_text(combo),
                          "stake_units": rule.stake_units, VALUE: value}
                         for combo, value in zip(combos, values, strict=True) if rule.value_line is None or value >= rule.value_line]
            rows += [{**head, RULE: PLACE_LABEL, "ticket_type": TicketType.PLACE.label, "combo": combo, "stake_units": PLACE_STAKE_UNITS,
                      VALUE: np.nan} for combo in self._place_combos(race)]
        return pd.DataFrame(rows, columns=list(COLUMNS))

    def _horses_by_mark(self, race: pd.DataFrame) -> dict[str, list[int]]:
        """印 → 馬番の並び（3着以内の確率の高い順）。"""
        return {mark: [int(no) for no in group[HORSE_NO]] for mark, group in race.groupby(MARK, sort=False)}

    def _axes(self, race: pd.DataFrame, by_mark: dict[str, list[int]]) -> dict[str, int]:
        """パターン → 軸の馬番。◎ がいなければどちらの軸も無い。軸の列が無い（前の形の表）なら軸馬も ◎。"""
        tops = by_mark.get(TOP_MARK, [])
        if not tops:
            return {}
        flagged = race[race[AXIS].fillna(False).astype(bool)] if AXIS in race.columns else race.iloc[0:0]
        axis = int(flagged[HORSE_NO].iloc[0]) if len(flagged) else tops[0]
        return {TOP_AXIS: tops[0], HORSE_AXIS: axis}

    def _ratios(self, race: pd.DataFrame) -> pd.DataFrame:
        """馬番を index にした「モデル ÷ 市場」の比。市場の見立てや1着の確率の列が無ければ（木曜・前の形の表）欠損値。"""
        blank = pd.Series(np.nan, index=race.index)
        ratios = self._ratio.of(race[PROBABILITY], race.get(MARKET_TOP3, blank), race.get(WIN_PROBABILITY, blank), race.get(MARKET_WIN, blank))
        return ratios.set_axis(race[HORSE_NO].astype(int))

    def _values(self, rule: TicketRule | AxisTicketRule, combos: list[tuple[int, ...]], ratios: pd.DataFrame) -> np.ndarray:
        """組の期待値（軸から流す券種だけ。ほかは欠損値）。"""
        if isinstance(rule, AxisTicketRule):
            return self._value.of(rule.ticket_type, combos, ratios)
        return np.full(len(combos), np.nan)

    def _place_combos(self, race: pd.DataFrame) -> list[str]:
        """複勝: 期待値が線以上の馬を高い順に最大3点。"""
        priced = race[race[PLACE_VALUE] >= PLACE_VALUE_LINE].sort_values(PLACE_VALUE, ascending=False)
        return [combo_text((int(no),)) for no in priced[HORSE_NO].head(PLACE_MAX_POINTS)]
