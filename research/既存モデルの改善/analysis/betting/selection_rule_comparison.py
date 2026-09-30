"""1つの区切りで、勝負するレースの選び方の決まりごとに、検証期間で選び方を決めてテスト期間に買う。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from ..walk_forward import WINDOW
from ..windows import TestWindow
from .betting_plan_chooser import BettingPlanChooser
from .candidate_columns import RACE, RETURN, STAKE, TICKET
from .race_columns import GRADED
from .race_selection_rule import RaceSelectionRule

#: 買い目の表に足す、選び方の保存の名前の列。
RULE = "選び方"


class SelectionRuleComparison:
    """勝負するレースの選び方の決まり（``rules``）ごとに、同じ買い目の候補・同じ券種の線で買ったときを比べる。

    券種の線と買う券種は、決まりに依らず同じ（``BettingPlanChooser.choose_lines`` で決めたもの）。決まりごとに違うのは、
    勝負するレースの選び方（1開催日のレース数・堅さの帯・並べ方・重賞の数え方）だけ。選び方は、決まりの候補の中から
    検証期間の控えめな見積もりで決め、テスト期間の結果は使わない。
    """

    def __init__(self, chooser: BettingPlanChooser, rules: Sequence[RaceSelectionRule]) -> None:
        self._chooser = chooser
        self._rules = tuple(rules)

    def run(self, window: TestWindow, lines: Mapping[str, float], adopted: frozenset[str], history: pd.DataFrame,
            history_races: pd.DataFrame, test_tickets: pd.DataFrame,
            test_races: pd.DataFrame) -> tuple[list[dict[str, object]], pd.DataFrame]:
        """（決まりごとの記録の行, 決まりごとにテスト期間に買った買い目。``RULE`` と ``WINDOW`` の列つき）。"""
        results = [self._rule(rule, window, lines, adopted, history, history_races, test_tickets, test_races)
                   for rule in self._rules]
        records = [record for record, _ in results]
        frames = [frame for _, frame in results]
        return records, pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def _rule(self, rule: RaceSelectionRule, window: TestWindow, lines: Mapping[str, float], adopted: frozenset[str],
              history: pd.DataFrame, history_races: pd.DataFrame, test_tickets: pd.DataFrame,
              test_races: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
        plan = self._chooser.choose_selection(rule, lines, adopted, history, history_races)
        bought = plan.apply(test_tickets, test_races)[[RACE, TICKET, STAKE, RETURN]]
        stake, payout = float(bought[STAKE].sum()), float(bought[RETURN].sum())
        graded = set(test_races.loc[test_races[GRADED].fillna(False).astype(bool), RACE])
        record = {
            WINDOW: window.name, RULE: rule.name, "検証期間で選んだ選び方": plan.describe(),
            "検証の控えめな見積もり": self._chooser.score(plan, history, history_races),
            "テストの勝負したレース数": int(bought[RACE].nunique()),
            "うち重賞": int(bought.loc[bought[RACE].isin(graded), RACE].nunique()),
            "テストの投資（円）": int(stake), "テストの払戻（円）": int(payout),
            "テストの回収率": payout / stake if stake > 0 else float("nan"),
        }
        return record, bought.assign(**{WINDOW: window.name, RULE: rule.key})
