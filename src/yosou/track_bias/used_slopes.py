"""当日の傾きと過去の傾きを混ぜて、使う傾きにする。"""

from __future__ import annotations

import pandas as pd

from . import names

#: 過去の傾きの重み k（設計書「買うレースと買い目を決める」06 の 1 の初めの値）。当日のレースが k 本たまると、当日と過去が半々になる。
PRIOR_WEIGHT = 4.0


class UsedSlopes:
    """使う傾き = （n × 当日の傾き + k × 過去の傾き）÷（n + k）。n は当日に数えたレースの数（``DaySlopes``）、k は ``PRIOR_WEIGHT``。

    当日の傾きが無い（n = 0 か、その傾きの出るレースが無い）ときは過去の傾きをそのまま使う。
    例（架空）: 当日3レースで内の傾き +0.12、過去の内の傾き +0.04 なら、(3 × 0.12 + 4 × 0.04) ÷ 7 = +0.074。
    """

    def of(self, day: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
        """``day``（``DaySlopes.of`` の表）と ``prior``（``PriorSlopeTable.lookup`` の表。同じ index）から、列 ``使う内の傾き``・``使う前の傾き``。
        いつもの傾き（``COURSE_INNER``・``COURSE_FRONT``）は、補正で引くためにそのまま添える（``prior`` に無ければ 0）。"""
        races = day[names.RACES].astype("float64")
        usual = prior.reindex(columns=[names.COURSE_INNER, names.COURSE_FRONT]).fillna(0.0)
        return pd.DataFrame({
            names.USED_INNER: self._mix(day[names.INNER_SLOPE], prior[names.PRIOR_INNER], races),
            names.USED_FRONT: self._mix(day[names.FRONT_SLOPE], prior[names.PRIOR_FRONT], races),
            names.COURSE_INNER: usual[names.COURSE_INNER].to_numpy(), names.COURSE_FRONT: usual[names.COURSE_FRONT].to_numpy(),
        }, index=day.index)

    def _mix(self, today: pd.Series, past: pd.Series, races: pd.Series) -> pd.Series:
        counted = races.where(today.notna(), 0.0)
        return (counted * today.fillna(0.0) + PRIOR_WEIGHT * past) / (counted + PRIOR_WEIGHT)
