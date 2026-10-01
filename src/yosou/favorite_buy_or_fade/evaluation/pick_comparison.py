"""1番人気の選び方（確定オッズ・締め切り前のオッズ）で、判定と回収率がどれだけ変わるかを表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import HORSE_NO, RACE_ID

from ..dataset import PICK
from ..decision import DECISION
from .decision_summary import COLUMNS, DecisionSummary
from .stake_plan import StakePlan

#: 選び方が1つしか無いとき（いつもの評価）は、比べる表を出さない。
_MIN_PICKS = 2


class PickComparison:
    """同じレースで、確定オッズで選んだ1番人気と、締め切り前のオッズで選んだ1番人気の判定を比べる（設計書 16 の 7）。

    - 1番人気が入れ替わったレースの数と、そのうち判定まで変わったレースの数。
    - 選び方ごとの、消し・単勝の当たり具合と回収率（全部のレースと、1番人気が入れ替わったレースだけ）。
    同じ馬なら特徴量も同じなので判定も同じになる。違いは、1番人気が入れ替わったレースからだけ生まれる。
    """

    def __init__(self, plan: StakePlan) -> None:
        self._summary = DecisionSummary(plan)

    def tables(self, rows: pd.DataFrame) -> list[Table]:
        """``rows`` は ``YearlyEvaluation`` の結果。選び方が1つしか無ければ、空の並び。"""
        if rows[PICK].nunique() < _MIN_PICKS:
            return []
        changed = self._changed_races(rows)
        return [self._counts(rows, changed),
                self._by_pick(rows, "選び方ごとの結果（同じレース）"),
                self._by_pick(rows[rows[RACE_ID].isin(changed.index[changed])], "選び方ごとの結果（1番人気が入れ替わったレースだけ）")]

    def _changed_races(self, rows: pd.DataFrame) -> pd.Series:
        """レースID → 1番人気（の馬番の組）が選び方で違ったか。"""
        horses = rows.groupby([RACE_ID, PICK])[HORSE_NO].agg(lambda numbers: tuple(sorted(numbers))).unstack(PICK)
        return horses.nunique(axis=1, dropna=False) > 1

    def _counts(self, rows: pd.DataFrame, changed: pd.Series) -> Table:
        decisions = rows.groupby([RACE_ID, PICK])[DECISION].agg(lambda kinds: tuple(sorted(kinds))).unstack(PICK)
        decision_changed = decisions.nunique(axis=1, dropna=False) > 1
        record = [len(changed), int(changed.sum()), int((changed & decision_changed).sum())]
        return Table(["レース", "1番人気が入れ替わったレース", "そのうち判定も変わったレース"], [record],
                     title="確定オッズと締め切り前のオッズで、1番人気と判定が変わったレース",
                     note="締め切り前のオッズの断面があり、その1番人気が出走したレースだけを数える。")

    def _by_pick(self, rows: pd.DataFrame, title: str) -> Table:
        records = [[str(pick), *self._summary.summarize(part).values()] for pick, part in rows.groupby(PICK, sort=True)]
        return Table([PICK, *COLUMNS], records, title=title,
                     note="払戻は確定の払戻。どちらの選び方も、同じ年は同じモデル（確定の1番人気で学習）で判定した。")
