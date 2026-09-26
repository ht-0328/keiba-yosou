"""年ごとに学習し直すときの期間。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .forecast_group import ForecastGroup

#: 検証データ（早期終了と、温度・λ）の始まりの月（予測する年の前の年の 10月1日から 12月31日まで。設計書 16 の 7）。
VALID_FIRST_MONTH = 10


@dataclass(frozen=True)
class YearPeriod:
    """1つの組の、1つの年の期間。どれも「この日から、次の区切りの前日まで」。"""

    train_first_day: date
    valid_first_day: date
    predict_first_day: date
    predict_end_day: date


class WalkForwardSchedule:
    """年ごとの学習・検証・予測の期間を決める（設計書 16 の 7）。

    予測する年 y の学習は、組の最初の年の1月1日 〜（y−1）年9月30日、検証は（y−1）年10月1日 〜 12月31日、
    予測は y年1月1日 〜 12月31日。どの年も、その年の1月1日の時点で持っていたデータだけで予想したことになる。
    """

    def periods(self, group: ForecastGroup, year: int) -> YearPeriod:
        """組の最初の年より前の年を予測しようとしたら ``ValueError``。"""
        if year <= group.first_train_year:
            raise ValueError(f"{group.label}の組は、{group.first_train_year + 1}年からしか予測できません: {year}年")
        return YearPeriod(
            date(group.first_train_year, 1, 1), date(year - 1, VALID_FIRST_MONTH, 1), date(year, 1, 1), date(year + 1, 1, 1),
        )

    def first_year(self, group: ForecastGroup) -> int:
        """その組が予測を出せる最初の年。"""
        return group.first_train_year + 1
