"""検証期間の成績で、買い方の線（``BettingPlan``）を決める。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_DATE

from yosou.shared.betting import TicketType

from ..scores.conservative_rate import ConservativeRate
from .betting_plan import BettingPlan
from .candidate_columns import RACE, RETURN, SET_VALUE, STAKE, TICKET
from .race_selection_rule import RaceSelectionRule
from .selection_rules import CURRENT_RULE

#: 券種全体の期待値の線の候補。
SET_LINE_CANDIDATES: tuple[float, ...] = (1.0, 1.1, 1.2, 1.3, 1.5)


@dataclass(frozen=True)
class TicketChoice:
    """1つの券種について、検証期間で選んだ券種全体の期待値の線と、そのときの検証期間の成績（金額で）。"""

    ticket: str
    line: float
    races: int
    points: int
    hits: int
    stake: float
    payout: float
    rate: float
    conservative: float
    adopted: bool


class BettingPlanChooser:
    """検証期間の買い目から、買い方の線を決める（テスト期間の結果は使わない）。

    1. 券種ごとに、券種全体の期待値の線の候補のうち、**当たりが ``min_hits`` 回以上**あるものの中から、
       **回収率の控えめな見積もり**（``ConservativeRate``。金額で）がいちばん高い線を選ぶ。回収率が 100% 以上なら、その券種を買う。
    2. 勝負するレースの選び方の決まり（``RaceSelectionRule``）の、1開催日のレース数の候補 × 堅さの帯の候補ごとに、
       選んだ線で買った全体の控えめな見積もりを比べ、いちばん高いものを選ぶ
       （買う券種が1つも無ければ、全券種を買ったときで比べる）。
    """

    def __init__(self, min_hits: int = 30, rule: RaceSelectionRule = CURRENT_RULE,
                 lines: Sequence[float] = SET_LINE_CANDIDATES) -> None:
        self._min_hits = min_hits
        self._rule = rule
        self._lines = tuple(lines)
        self._conservative = ConservativeRate()

    def choose(self, tickets: pd.DataFrame, races: pd.DataFrame) -> tuple[BettingPlan, list[TicketChoice]]:
        """（選んだ買い方, 券種ごとの選び方）。"""
        lines, adopted, choices = self.choose_lines(tickets, races)
        return self.choose_selection(self._rule, lines, adopted, tickets, races), choices

    def choose_lines(self, tickets: pd.DataFrame,
                     races: pd.DataFrame) -> tuple[dict[str, float], frozenset[str], list[TicketChoice]]:
        """（券種 → 線, 買う券種, 券種ごとの選び方）。勝負するレースの選び方には依らない。"""
        dated = tickets.merge(races[[RACE, RACE_DATE]], on=RACE, how="left")
        choices = [self._ticket(ticket.label, dated[dated[TICKET] == ticket.label]) for ticket in TicketType]
        found = [choice for choice in choices if not np.isnan(choice.line)]
        lines = {choice.ticket: choice.line for choice in found}
        adopted = frozenset(choice.ticket for choice in found if choice.adopted)
        return lines, adopted, choices

    def choose_selection(self, rule: RaceSelectionRule, lines: Mapping[str, float], adopted: frozenset[str],
                         tickets: pd.DataFrame, races: pd.DataFrame) -> BettingPlan:
        """決まり ``rule`` の候補の中から、検証期間の控えめな見積もりがいちばん高い勝負するレースの選び方。"""
        plans = [BettingPlan(per_day, dict(lines), adopted, band, rule.excluded_first, rule.graded_in_cap)
                 for per_day in rule.per_day for band in rule.bands]
        return max(plans, key=lambda plan: self.score(plan, tickets, races))

    def score(self, plan: BettingPlan, tickets: pd.DataFrame, races: pd.DataFrame) -> float:
        """その買い方で検証期間に買ったときの、回収率の控えめな見積もり（買うものが無ければ −∞）。"""
        chosen = plan if plan.adopted else plan.with_all_tickets()
        bought = chosen.apply(tickets, races).merge(races[[RACE, RACE_DATE]], on=RACE, how="left")
        if bought.empty:
            return -np.inf
        value = self._conservative.of(bought[RACE_DATE], bought[STAKE], bought[RETURN])
        return -np.inf if np.isnan(value) else value

    def _ticket(self, ticket: str, rows: pd.DataFrame) -> TicketChoice:
        results = [self._evaluate(ticket, line, rows[rows[SET_VALUE] >= line]) for line in self._lines]
        eligible = [result for result in results if result.hits >= self._min_hits and not np.isnan(result.conservative)]
        if not eligible:
            return TicketChoice(ticket, float("nan"), 0, 0, 0, 0.0, 0.0, float("nan"), float("nan"), False)
        return max(eligible, key=lambda result: result.conservative)

    def _evaluate(self, ticket: str, line: float, bought: pd.DataFrame) -> TicketChoice:
        stake, payout = float(bought[STAKE].sum()), float(bought[RETURN].sum())
        rate = payout / stake if stake > 0 else float("nan")
        conservative = self._conservative.of(bought[RACE_DATE], bought[STAKE], bought[RETURN]) if stake > 0 else float("nan")
        return TicketChoice(ticket, line, int(bought[RACE].nunique()), len(bought), int((bought[RETURN] > 0).sum()),
                            stake, payout, rate, conservative, rate >= 1.0)
