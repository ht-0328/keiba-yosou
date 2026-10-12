"""第3段: 選んだレースごとに、買い方に従って買い目（1行 = 1点）を作る。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID
from yosou.upset_premise.betting import RaceHorses, TicketPlan

#: 買い目の表の列の名前。
PLAN, COMBO, STAKE, ODDS = "買い方", "組", "掛け金", "オッズ"


class TicketMaker:
    """選んだレース（``races`` の レースID・開催日）ごとに、``plan`` で買い目を作り、1行 = 1点の表にする。

    ``horses`` はレースID → 出走馬ごとの予想、``odds`` は券種（3連単は真・3連複は偽）→ レースID → 組 → 確定オッズ。
    予想かオッズの無いレースは買わない。``label`` は表に出す買い方の名前（予想の名前を添えるため）。
    """

    def __init__(self, plan: TicketPlan, label: str) -> None:
        self._plan = plan
        self._label = label

    def make(self, races: pd.DataFrame, horses: Mapping[str, RaceHorses],
             odds: Mapping[bool, Mapping[str, Mapping[tuple[int, ...], float]]]) -> pd.DataFrame:
        pool = odds[self._plan.ordered]
        rows = [self._rows(race_id, day, horses[race_id], pool[race_id])
                for race_id, day in zip(races[RACE_ID], races[RACE_DATE]) if race_id in horses and race_id in pool]
        flat = [row for race_rows in rows for row in race_rows]
        return pd.DataFrame(flat, columns=[PLAN, RACE_ID, RACE_DATE, COMBO, STAKE, ODDS])

    def _rows(self, race_id: str, day: pd.Timestamp, horses: RaceHorses,
              odds: Mapping[tuple[int, ...], float]) -> list[tuple[object, ...]]:
        return [(self._label, race_id, day, combo, stake, odds[combo]) for combo, stake in self._plan.tickets(horses, odds)]
