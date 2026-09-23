"""1レースの買い目を作る。"""

from __future__ import annotations

import pandas as pd

from ..column_names import HORSE_NO, POPULARITY, WIN_ODDS
from .column_rule import ColumnRule
from .dangerous_favorite_filter import DangerousFavoriteFilter
from .formation_tickets import FormationTickets
from .picker import FormRankPicker
from .plan_tickets import PlanTickets
from .ticket_plan import TicketPlan

#: 見送りの理由（結果の表に出す）。
SKIP_NO_CANDIDATES = "候補が足りない"
SKIP_TOP_NOT_FAVORITE = "本命が1番人気でない"
SKIP_LOW_ODDS = "本命のオッズが低い"
#: 本命 = 1番人気 の判定に使う人気順位。
_FIRST_POPULARITY = 1


class TicketBuilder:
    """1レースの runners と ``TicketPlan`` から買い目を作る。

    手順: 危険な人気馬を外す → 買う条件（本命が1番人気か・本命のオッズ）を確かめる → 列を順に埋める →
    ``FormationTickets`` で組み合わせる。列が1つでも空なら見送り。確定オッズで削るのは精算のとき（``settlement/``）。
    """

    def __init__(self, plan: TicketPlan, dangerous_filter: DangerousFavoriteFilter | None = None,
                 formation: FormationTickets | None = None) -> None:
        self._plan = plan
        self._dangerous_filter = dangerous_filter or DangerousFavoriteFilter()
        self._formation = formation or FormationTickets()
        self._top_picker = FormRankPicker()

    def build(self, runners: pd.DataFrame) -> PlanTickets:
        candidates = self._candidates(runners)
        skipped = self._precheck(candidates)
        if skipped is not None:
            return PlanTickets.skip(skipped)
        columns = self._columns(candidates)
        if any(len(column) == 0 for column in columns):
            return PlanTickets.skip(SKIP_NO_CANDIDATES)
        return PlanTickets(tuple(self._formation.build(self._plan.ticket_type, columns)))

    def _candidates(self, runners: pd.DataFrame) -> pd.DataFrame:
        if self._plan.excludes_dangerous:
            return self._dangerous_filter.apply(runners)
        return runners

    def _precheck(self, candidates: pd.DataFrame) -> str | None:
        """買う条件に合わないときの理由。合えば None。"""
        top = self._top_picker.pick(candidates, 1, ())
        if not top:
            return SKIP_NO_CANDIDATES
        row = candidates[candidates[HORSE_NO] == top[0]].iloc[0]
        if self._plan.requires_top_favorite and row[POPULARITY] != _FIRST_POPULARITY:
            return SKIP_TOP_NOT_FAVORITE
        if self._plan.min_first_odds is not None and self._first_odds(candidates) < self._plan.min_first_odds:
            return SKIP_LOW_ODDS
        return None

    def _first_odds(self, candidates: pd.DataFrame) -> float:
        """1列目の先頭の馬の単勝オッズ（無ければ 0 とみなして見送る）。"""
        first = self._plan.columns[0].picker.pick(candidates, 1, ())
        if not first:
            return 0.0
        odds = candidates[candidates[HORSE_NO] == first[0]][WIN_ODDS].iloc[0]
        return float(odds) if pd.notna(odds) else 0.0

    def _columns(self, candidates: pd.DataFrame) -> list[list[int]]:
        """列を順に埋める。先の列で使った馬は、あとの列の新しい候補にしない。"""
        columns: list[list[int]] = []
        taken: set[int] = set()
        for rule in self._plan.columns:
            column = self._column(rule, candidates, columns, taken)
            taken |= set(column)
            columns.append(column)
        return columns

    def _column(self, rule: ColumnRule, candidates: pd.DataFrame, previous: list[list[int]], taken: set[int]) -> list[int]:
        """1列ぶん。同じ列の写し → 前の列を含める → 選び方で足す、の順。"""
        if rule.same_as is not None:
            return list(previous[rule.same_as])
        base = list(previous[-1]) if rule.keeps_previous and previous else []
        picked = rule.picker.pick(candidates, rule.count - len(base), taken)
        return base + picked
