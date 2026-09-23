"""1つの戦略を評価する。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import RACE_DATE, RACE_ID
from ..participation import ConfidenceJudge, RacePattern, UpsetJudge
from ..settlement import SettlementTable
from ..settlement.settlement_table import HIT_COUNT, PAYOUT_YEN, POINTS, STAKE_YEN
from ..summary import ReturnSummary
from ..ticket import plan_named
from .strategy import Strategy
from .strategy_result import StrategyResult

#: レース単位に足す列。
_SUM_COLUMNS: list[str] = [POINTS, STAKE_YEN, PAYOUT_YEN, HIT_COUNT]
_MONTH_FORMAT = "%Y-%m"


class StrategyEvaluator:
    """戦略を、期間のレース（材料表の races）と精算表で評価する。

    参加パターンで買うレースを決め、広めの買い方の行と少点数の買い方の行を精算表から取り出し、レース単位に足してからまとめる
    （同じレースを両方で買えば、そのレースの点数・払戻は両方の合計）。精算表はしきい値に依存しないので、ここでは足すだけ。
    """

    def __init__(self, settlement: SettlementTable, patterns: Mapping[str, RacePattern]) -> None:
        self._plan_rows = {name: settlement.for_plan(name) for name in settlement.plan_names}
        self._patterns = dict(patterns)

    def evaluate(self, strategy: Strategy, races: pd.DataFrame) -> StrategyResult:
        pattern = self._patterns[strategy.pattern_key]
        judges = (UpsetJudge(strategy.upset_threshold), ConfidenceJudge(strategy.form_threshold, strategy.danger_threshold))
        participation = pattern.select(races, *judges, self._wide_bet(strategy), strategy.top_k)
        wide_rows = self._rows(strategy.wide_plan, participation.wide_ids)
        narrow_rows = self._rows(strategy.narrow_plan, participation.narrow_ids)
        per_race = self._per_race(wide_rows, narrow_rows)
        return StrategyResult(
            strategy, participation.race_count, len(participation.wide_ids), len(participation.narrow_ids),
            participation.selected_count, ReturnSummary.from_rows(per_race),
            self._summary_or_none(strategy.wide_plan, wide_rows), self._summary_or_none(strategy.narrow_plan, narrow_rows),
            self._by_month(per_race, races),
        )

    def _wide_bet(self, strategy: Strategy) -> BetType:
        """荒れ判定に使う券種（広めの買い方の券種に対応するもの。広めが無ければ単勝）。"""
        if strategy.wide_plan is None:
            return BetType.WIN
        return plan_named(strategy.wide_plan).ticket_type.spec.upset_bet

    def _rows(self, plan_name: str | None, race_ids: Sequence[str]) -> pd.DataFrame:
        """その買い方の精算表の行のうち、選んだレースのもの。"""
        if plan_name is None:
            return self._empty()
        if plan_name not in self._plan_rows:
            raise LookupError(f"精算表に無い買い方です: {plan_name}（先に --settle-only を実行してください）")
        rows = self._plan_rows[plan_name]
        return rows[rows.index.isin(race_ids)][_SUM_COLUMNS]

    def _per_race(self, wide_rows: pd.DataFrame, narrow_rows: pd.DataFrame) -> pd.DataFrame:
        """広めと少点数の行を、レース単位に足す。"""
        combined = pd.concat([wide_rows, narrow_rows])
        if combined.empty:
            return self._empty()
        return combined.groupby(level=0)[_SUM_COLUMNS].sum()

    def _by_month(self, per_race: pd.DataFrame, races: pd.DataFrame) -> dict[str, ReturnSummary]:
        if per_race.empty:
            return {}
        months = races.set_index(RACE_ID)[RACE_DATE].dt.strftime(_MONTH_FORMAT).reindex(per_race.index)
        return {str(month): ReturnSummary.from_rows(group) for month, group in per_race.groupby(months)}

    def _summary_or_none(self, plan_name: str | None, rows: pd.DataFrame) -> ReturnSummary | None:
        return ReturnSummary.from_rows(rows) if plan_name is not None else None

    def _empty(self) -> pd.DataFrame:
        return pd.DataFrame({column: pd.Series(dtype="int64") for column in _SUM_COLUMNS})
