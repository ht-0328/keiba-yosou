"""検証期間の成績で、印の買い方の線（``MarkPlan``）を決める。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_DATE

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..scores.conservative_rate import ConservativeRate
from .candidate_columns import RACE, TICKET, VALUE
from .mark_plan import MarkPlan
from .payout_table import PAYOUT

#: 1開催日に勝負する上位のレース数の候補。
PER_DAY_CANDIDATES: tuple[int, ...] = (3, 5, 10)
#: 「◎が危うい」とする◎の3着以内の確率の線の候補（0 は、◎が人気馬で危険度が正のときだけ）。
SHAKY_CANDIDATES: tuple[float, ...] = (0.0, 0.5, 0.6)
#: 期待値の線の候補（これより低い買い目はカットする）。
VALUE_CANDIDATES: tuple[float, ...] = (0.8, 0.9, 1.0, 1.1, 1.2)
#: 1点の賭け金（円）。
_STAKE = 100.0


@dataclass(frozen=True)
class TicketChoice:
    """1つの券種について、検証期間で選んだ期待値の線と、そのときの検証期間の成績。"""

    ticket: str
    line: float
    points: int
    races: int
    hits: int
    rate: float
    conservative: float
    adopted: bool


class MarkPlanChooser:
    """検証期間の買い目の候補から、印の買い方の線を決める（テスト期間の結果は使わない）。

    1. 1開催日のレース数 × 「◎が危うい」の線 の組ごとに、勝負するレースと押さえを決める。
    2. 券種ごとに、期待値の線の候補のうち、**当たりが ``min_hits`` 回以上**あるものの中から、**回収率の控えめな見積もり**
       （``ConservativeRate``）がいちばん高い線を選ぶ。検証期間の回収率が 100% 以上なら、その券種を買う。
    3. 買う券種を合わせた控えめな見積もりがいちばん高い組を選ぶ（買う券種が1つも無い組しかなければ、全券種で比べる）。

    「回収率がいちばん高い」で選ばないのは、当たりの少ない券種では数回の大当たりで高く見えてしまうため。
    """

    def __init__(self, min_hits: int = 30, per_day: Sequence[int] = PER_DAY_CANDIDATES,
                 shaky: Sequence[float] = SHAKY_CANDIDATES, values: Sequence[float] = VALUE_CANDIDATES) -> None:
        self._min_hits = min_hits
        self._per_day = tuple(per_day)
        self._shaky = tuple(shaky)
        self._values = tuple(values)
        self._conservative = ConservativeRate()

    def choose(self, candidates: pd.DataFrame, races: pd.DataFrame) -> tuple[MarkPlan, list[TicketChoice]]:
        """（選んだ買い方, 券種ごとの選び方）。"""
        options = [self._option(MarkPlan(per_day, shaky), candidates, races) for per_day, shaky in product(self._per_day, self._shaky)]
        return max(options, key=lambda option: self._score(option[0], candidates, races))

    def _option(self, plan: MarkPlan, candidates: pd.DataFrame, races: pd.DataFrame) -> tuple[MarkPlan, list[TicketChoice]]:
        rows = self._with_dates(plan.base_rows(candidates, races), races)
        choices = [self._ticket(ticket.label, rows[rows[TICKET] == ticket.label]) for ticket in TicketType]
        found = [choice for choice in choices if not np.isnan(choice.line)]
        lines = {choice.ticket: choice.line for choice in found}
        adopted = frozenset(choice.ticket for choice in found if choice.adopted)
        return MarkPlan(plan.races_per_day, plan.shaky_line, lines, adopted), choices

    def _score(self, plan: MarkPlan, candidates: pd.DataFrame, races: pd.DataFrame) -> tuple[int, float]:
        """組の比べ方: 買う券種がある組を先に、その中で控えめな見積もりが高いもの。"""
        chosen = plan if plan.adopted else plan.with_all_tickets()
        rows = self._with_dates(chosen.apply(candidates, races), races)
        value = self._conservative.of(rows[RACE_DATE], pd.Series(_STAKE, index=rows.index), rows[PAYOUT]) if len(rows) else np.nan
        return int(bool(plan.adopted)), -np.inf if np.isnan(value) else value

    def _ticket(self, ticket: str, rows: pd.DataFrame) -> TicketChoice:
        results = [self._evaluate(ticket, line, rows[rows[VALUE] >= line]) for line in self._values]
        eligible = [result for result in results if result.hits >= self._min_hits and not np.isnan(result.conservative)]
        if not eligible:
            return TicketChoice(ticket, float("nan"), 0, 0, 0, float("nan"), float("nan"), False)
        return max(eligible, key=lambda result: result.conservative)

    def _evaluate(self, ticket: str, line: float, bought: pd.DataFrame) -> TicketChoice:
        points = len(bought)
        payout = bought[PAYOUT]
        rate = float(payout.sum() / (_STAKE * points)) if points else float("nan")
        conservative = self._conservative.of(bought[RACE_DATE], pd.Series(_STAKE, index=bought.index), payout) if points else float("nan")
        return TicketChoice(ticket, line, points, int(bought[RACE].nunique()), int((payout > 0).sum()), rate, conservative,
                            rate >= 1.0)

    def _with_dates(self, rows: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        return rows.merge(races[[RACE, RACE_DATE]], on=RACE, how="left")
