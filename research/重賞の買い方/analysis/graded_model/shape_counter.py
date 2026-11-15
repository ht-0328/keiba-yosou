"""形の候補ごと・重賞ごとに、買い目の点数・払戻・組の期待値の平均を数える。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from 今週の予想.mark_tickets import ODDS
from 印の成績.ticket_payouts import PAYOUT

from .combo_universe import COMBO, TICKET, VALUE
from .race_horses import RaceHorses
from .ticket_shape import MAX_POINTS, TicketShape, combo_key

#: 結果の列。
SHAPE, POINTS, RETURN, MEAN_VALUE = "shape", "points", "return", "mean_value"


class ShapeCounter:
    """印を付けた表（``marked``）と組の表（``ComboUniverse.build``）から、形ごと・重賞ごとに買い目を組んで数える（1行 = 形 × 重賞）。

    組み方: 形の組 → オッズの無い組を外す → オッズの上限・最低オッズの下限・期待値の線で外す → ``MAX_POINTS`` を超えたら期待値の高い順に残す →
    トリガミ（どれが当たっても、その券種の投資より戻りが少ない組）を外す（設計書 16 の 6.1）。1点は 100円。
    列は race_id・race_date・shape（``shapes`` の中の番号）・points（点数）・return（払戻）・mean_value（買った組の期待値の平均）。
    """

    def count(self, marked: pd.DataFrame, universe: pd.DataFrame, shapes: Sequence[TicketShape]) -> pd.DataFrame:
        priced = {(row.race_id, row.ticket, row.combo): (row.odds, row.payout, row.value)
                  for row in universe.rename(columns={ODDS: "odds", PAYOUT: "payout", TICKET: "ticket", COMBO: "combo",
                                                      VALUE: "value"}).itertuples(index=False)}
        rows = []
        for race_id, race in marked.groupby("race_id", sort=False):
            horses = RaceHorses.of(race)
            race_date = race["race_date"].iloc[0]
            for index, shape in enumerate(shapes):
                bought = self._bought(shape, [priced.get((race_id, shape.ticket, combo_key(shape.ticket, combo))) for combo in shape.combos(horses)])
                rows.append({"race_id": race_id, "race_date": race_date, SHAPE: index, POINTS: len(bought),
                             RETURN: float(sum(payout for _, payout, _ in bought)),
                             MEAN_VALUE: float(np.mean([value for _, _, value in bought])) if bought else np.nan})
        return pd.DataFrame(rows)

    def _bought(self, shape: TicketShape, priced: list) -> list[tuple[float, float, float]]:
        kept = [entry for entry in priced if entry is not None and pd.notna(entry[0]) and entry[0] > 0]
        if shape.cap is not None:
            kept = [entry for entry in kept if entry[0] <= shape.cap]
        if shape.floor is not None:
            kept = [entry for entry in kept if entry[0] >= shape.floor]
        if shape.line is not None:
            kept = [entry for entry in kept if pd.notna(entry[2]) and entry[2] >= shape.line]
        if len(kept) > MAX_POINTS:
            kept = sorted(kept, key=lambda entry: -(entry[2] if pd.notna(entry[2]) else -np.inf))[:MAX_POINTS]
        kept = sorted(kept, key=lambda entry: -entry[0])
        while kept and kept[-1][0] <= len(kept):
            kept = kept[:-1]
        return kept
