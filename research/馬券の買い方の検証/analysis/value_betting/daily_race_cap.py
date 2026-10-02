"""枠B「レースを選ぶ」: 見込みの利益の大きい順に、1開催日3レースまで（平地の重賞は別枠）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE as RACE_DATE_JA

from 既存モデルの改善.analysis.betting.race_columns import GRADED as GRADED_JA
from 既存モデルの改善.analysis.betting.race_columns import SCORE
from 既存モデルの改善.analysis.betting.race_selector import RaceSelector

from . import columns as c
from .protocol import RACES_PER_DAY

_RACE_KEY = [c.WINDOW, c.PART, c.RACE_ID]


class DailyRaceCap:
    """枠A の買い目（``CandidatePicker`` の表）があるレースを、開催日ごとに見込みの利益 E = Σ（期待値 − 1）× 賭け金 の
    大きい順に並べ、上位 ``per_day`` レースまで残す。平地の重賞は枠の外で、買い目があれば必ず残す。

    並べ方と重賞の数え方は、研究「既存モデルの改善」の ``RaceSelector``（``cap3``。期待値の順・重賞は別枠）をそのまま使う。
    危険な人気馬・荒れ具合は並べ方に使わない。区切り × 期間 ごとに分けて選ぶ（同じ開催日が隣の区切りにも出るため）。
    残した買い目の表には、レースの見込みの利益（``race_profit``）を足す。
    """

    def __init__(self, per_day: int = RACES_PER_DAY) -> None:
        self._selector = RaceSelector(per_day, excluded_first=False, graded_in_cap=False)

    def apply(self, tickets: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return tickets.assign(**{c.RACE_PROFIT: pd.Series(dtype=float)})
        profit = tickets.assign(_profit=(tickets[c.PLACE_VALUE] - 1.0) * tickets[c.STAKE_YEN]) \
            .groupby(_RACE_KEY, as_index=False)["_profit"].sum().rename(columns={"_profit": c.RACE_PROFIT})
        table = races[_RACE_KEY + [c.RACE_DATE, c.IS_GRADED]].merge(profit, on=_RACE_KEY, how="inner")
        chosen = pd.concat([group[self._selected(group)] for _, group in table.groupby([c.WINDOW, c.PART], sort=False)])
        keys = chosen[_RACE_KEY + [c.RACE_PROFIT]]
        return tickets.merge(keys, on=_RACE_KEY, how="inner").reset_index(drop=True)

    def _selected(self, group: pd.DataFrame) -> pd.Series:
        """1つの区切り × 期間 のレースごとに、残すか。"""
        frame = pd.DataFrame({
            RACE_DATE_JA: group[c.RACE_DATE].to_numpy(), GRADED_JA: group[c.IS_GRADED].fillna(False).astype(bool).to_numpy(),
            SCORE: group[c.RACE_PROFIT].to_numpy(),
        }, index=group.index)
        return self._selector.select(frame)
