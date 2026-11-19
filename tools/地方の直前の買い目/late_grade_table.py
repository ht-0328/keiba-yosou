"""レースを期待度（線への近さの S・A・B・C）で分けて、線にいちばん近い馬の単勝の成績を表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from yosou.shared.race_grade import GRADES, LocalExpectationScale

from .late_columns import HORSE_NO, RACE_DATE, RACE_ID
from .late_rule import LateRule

#: 表の列。
HEADERS: tuple[str, ...] = ("期間", "期待度", "レース数", "割合", "単勝の的中率", "単勝の回収率")
STAKE = 100
_RATIO, _PAYOUT, _GRADE = "ratio", "payout", "grade"


class LateGradeTable:
    """``scored`` は2つのモデルの値の付いた表（1頭1行。``LateWalkForward.run``）、``wins`` は単勝の払戻（``race_id``・``horse_no``・``payout``）。
    レースごとに、線にいちばん近い馬（``LateRule.ratios`` がいちばん大きい馬）を1頭選び、その値を期待度にして、その馬の単勝を 100円買ったときの
    成績を 全体・年 ごとに並べる。払戻の表に無いレース（結果がまだ無い・中止）は数えない。"""

    def __init__(self, rule: LateRule | None = None, scale: LocalExpectationScale | None = None) -> None:
        self._rule = rule or LateRule()
        self._scale = scale or LocalExpectationScale()

    def races(self, scored: pd.DataFrame, wins: pd.DataFrame) -> pd.DataFrame:
        """1レース1行: 線にいちばん近い馬・線への近さ・期待度・その馬の単勝の払戻（外れは 0）。"""
        rated = scored.assign(**{_RATIO: self._rule.ratios(scored), RACE_ID: scored[RACE_ID].astype(str)})
        closest = rated.loc[rated.groupby(RACE_ID)[_RATIO].idxmax(), [RACE_ID, RACE_DATE, HORSE_NO, _RATIO]]
        paid = wins.assign(**{RACE_ID: wins[RACE_ID].astype(str)})
        settled = closest[closest[RACE_ID].isin(set(paid[RACE_ID]))]
        merged = settled.merge(paid.groupby([RACE_ID, HORSE_NO], as_index=False)[_PAYOUT].sum(), on=[RACE_ID, HORSE_NO], how="left")
        return merged.assign(**{_PAYOUT: merged[_PAYOUT].fillna(0.0), _GRADE: merged[_RATIO].map(self._scale.of)})

    def table(self, scored: pd.DataFrame, wins: pd.DataFrame, title: str, note: str = "") -> Table:
        races = self.races(scored, wins)
        periods = [("全体", races)] + [(f"{year}年", part) for year, part in races.groupby(pd.to_datetime(races[RACE_DATE]).dt.year)]
        rows = [self._row(label, grade, part[part[_GRADE] == grade], len(part)) for label, part in periods for grade in GRADES]
        return Table(list(HEADERS), rows, title=title, note=note)

    @staticmethod
    def _row(label: str, grade: str, part: pd.DataFrame, total: int) -> list:
        if part.empty:
            return [label, grade, 0, "—", "—", "—"]
        return [label, grade, len(part), f"{len(part) / total:.1%}", f"{(part[_PAYOUT] > 0).mean():.1%}",
                f"{part[_PAYOUT].sum() / (STAKE * len(part)):.1%}"]
