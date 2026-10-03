"""印を付けた表から、券種ごとの買い目を作る。"""

from __future__ import annotations

from itertools import product

import pandas as pd

from yosou.shared.betting import TicketType

from 今週の予想.forecast_columns import EXPECTATION, HORSE_NO, MARK, PLACE_VALUE

from 印の成績.ticket_rules import (
    PLACE_MAX_POINTS,
    PLACE_STAKE_UNITS,
    PLACE_VALUE_LINE,
    TICKET_RULES,
    TicketRule,
    combo_text,
)

#: 買い目の表の列。
COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", EXPECTATION, "ticket_type", "combo", "stake_units")
#: レースから写す列。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", EXPECTATION)


class MarkTickets:
    """印を付けた表（``BacktestMarker.mark`` の戻り値。1行 = 1頭）から、印のルールの買い目（1行 = 1点）を作る
    （設計書「買うレースと買い目を決める」08 の 2。ルールは ``TICKET_RULES``）。

    - 印で組む券種: ルールの印の組み合わせを全部作り、同じ馬が2回入る組と、順不同の券種で並びだけが違う組は1点にまとめる
      （3連複の ◎−○−▲ と ◎−▲−○ は同じ1点）。印の付いた馬がいない位置（☆ の無いレースのワイドなど）は、その印を飛ばす。
    - 複勝: 複勝の期待値が線（1.25）以上の馬を、高い順に最大3点。
    列は ``COLUMNS``（``ticket_type`` は券種の名前、``combo`` は組番の文字列、``stake_units`` は1点の額の単位）。
    """

    def build(self, marked: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict] = []
        for _, race in marked.groupby("race_id", sort=False):
            head = {column: race[column].iloc[0] for column in _RACE_COLUMNS}
            by_mark = self._horses_by_mark(race)
            for rule in TICKET_RULES:
                rows += [{**head, "ticket_type": rule.ticket_type.label, "combo": combo, "stake_units": rule.stake_units}
                         for combo in self._combos(by_mark, rule)]
            rows += [{**head, "ticket_type": TicketType.PLACE.label, "combo": combo, "stake_units": PLACE_STAKE_UNITS}
                     for combo in self._place_combos(race)]
        return pd.DataFrame(rows, columns=list(COLUMNS))

    def _horses_by_mark(self, race: pd.DataFrame) -> dict[str, list[int]]:
        """印 → 馬番の並び（3着以内の確率の高い順）。"""
        return {mark: [int(no) for no in group[HORSE_NO]] for mark, group in race.groupby(MARK, sort=False)}

    def _combos(self, by_mark: dict[str, list[int]], rule: TicketRule) -> list[str]:
        choices = [[horse for mark in position for horse in by_mark.get(mark, [])] for position in rule.positions]
        if any(not choice for choice in choices):
            return []
        ordered = rule.ticket_type.spec.is_ordered
        combos = {self._normalize(combo, ordered) for combo in product(*choices) if len(set(combo)) == len(combo)}
        return [combo_text(combo) for combo in sorted(combos)]

    def _normalize(self, combo: tuple[int, ...], ordered: bool) -> tuple[int, ...]:
        return tuple(combo) if ordered else tuple(sorted(combo))

    def _place_combos(self, race: pd.DataFrame) -> list[str]:
        """複勝: 期待値が線以上の馬を高い順に最大3点。"""
        priced = race[race[PLACE_VALUE] >= PLACE_VALUE_LINE].sort_values(PLACE_VALUE, ascending=False)
        return [combo_text((int(no),)) for no in priced[HORSE_NO].head(PLACE_MAX_POINTS)]
