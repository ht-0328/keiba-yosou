"""買い方の、検証期間で決める線の組と、それに従った買い目の選び方。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

import pandas as pd

from ..ticket_combos import RACE_BUDGET
from .candidate_columns import RACE, SET_STAKE, SET_VALUE, TICKET
from .race_columns import SCORE
from .race_selector import RaceSelector


@dataclass(frozen=True)
class BettingPlan:
    """買い方で、検証期間で決める線の組。

    - ``set_lines``: 券種 → 券種全体の期待値の線。これ以上の券種だけを買う候補にする。
    - ``adopted``: テスト期間に買う券種（検証期間の成績で決めた）。
    - ``races_per_day``: 1開催日に勝負する上位のレース数（重賞は別枠）。None なら全部。

    1レースでは、全部の券種を買わない。線を超えた券種を、券種全体の期待値の高い順に、1レースの予算（5,000円）に
    入るところまで買う（券種で期待値を積む）。例: 3連単 1.35・馬連 1.20・単勝 0.95 で、単勝の線が 1.0 なら、
    3連単と馬連だけを買う。
    """

    races_per_day: int | None
    set_lines: Mapping[str, float] = field(default_factory=dict)
    adopted: frozenset[str] = frozenset()

    def apply(self, tickets: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """買う買い目。"""
        sets = self._stacked_sets(tickets)
        scores = sets.groupby(RACE)[SET_VALUE].max().rename(SCORE)
        candidates = races.merge(scores, left_on=RACE, right_index=True, how="inner")
        chosen = candidates[RaceSelector(self.races_per_day).select(candidates)][RACE]
        keys = sets[sets[RACE].isin(set(chosen))][[RACE, TICKET]]
        return tickets.merge(keys, on=[RACE, TICKET], how="inner").reset_index(drop=True)

    def _stacked_sets(self, tickets: pd.DataFrame) -> pd.DataFrame:
        """レース × 券種 のうち、買う券種で線を超えたものを、期待値の高い順に予算に入るところまで。"""
        sets = tickets.drop_duplicates([RACE, TICKET])[[RACE, TICKET, SET_VALUE, SET_STAKE]]
        lines = sets[TICKET].map(self.set_lines)
        passing = sets[sets[TICKET].isin(self.adopted) & (sets[SET_VALUE] >= lines)]
        ranked = passing.sort_values([RACE, SET_VALUE], ascending=[True, False], kind="stable")
        return ranked[ranked.groupby(RACE)[SET_STAKE].cumsum() <= RACE_BUDGET]

    def with_all_tickets(self) -> BettingPlan:
        """線の決まった券種を全部買う計画（参考: 検証期間で回収率 100% に届かなかった券種も買ったとき）。"""
        return replace(self, adopted=frozenset(self.set_lines))

    def describe(self) -> str:
        per_day = "全レース" if self.races_per_day is None else f"1開催日の上位 {self.races_per_day} レース＋重賞"
        return f"{per_day}（1番人気を消したレースを先に選ぶ）"
