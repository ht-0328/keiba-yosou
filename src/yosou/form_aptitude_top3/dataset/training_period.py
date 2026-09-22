"""学習データの期間（4つの区切りの日）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: 既定の区切り。ウォームアップの始まり → 学習データの始まり → 検証データの始まり → テストデータの始まり。
DEFAULT_WARMUP_FIRST_DAY = date(2023, 1, 1)
DEFAULT_TRAIN_FIRST_DAY = date(2024, 1, 1)
DEFAULT_VALID_FIRST_DAY = date(2025, 7, 1)
DEFAULT_TEST_FIRST_DAY = date(2026, 1, 1)
#: ``warmup_first_day`` を省略したときの、学習データの始まりからさかのぼる年数。
DEFAULT_WARMUP_YEARS = 1


@dataclass(frozen=True)
class TrainingPeriod:
    """学習データの期間を区切る4つの日（設計書 08 の 3）。古い順に並んでいなければ ``ValueError``。

    - ``warmup_first_day``: ウォームアップ期間の始まり。ここからの出走を読むが、サンプルにはせず、
      過去走の特徴量を計算するためだけに使う。
    - ``train_first_day``: 学習データの始まり。ここからの出走がサンプルになる。
    - ``valid_first_day``: 検証データの始まり（この前日までが学習データ）。
    - ``test_first_day``: テストデータの始まり（この前日までが検証データ）。
    """

    warmup_first_day: date
    train_first_day: date
    valid_first_day: date
    test_first_day: date

    def __post_init__(self) -> None:
        days = list(self.boundaries().items())
        for (name, day), (next_name, next_day) in zip(days, days[1:]):
            if day >= next_day:
                raise ValueError(
                    f"{name}（{day}）は、{next_name}（{next_day}）より前の日にしてください。"
                    "区切りは、ウォームアップ → 学習 → 検証 → テストの順に新しくなります。"
                )

    @classmethod
    def starting(cls, train_first_day: date, valid_first_day: date, test_first_day: date,
                 warmup_first_day: date | None = None) -> TrainingPeriod:
        """``warmup_first_day`` を省略すると、学習データの始まりの ``DEFAULT_WARMUP_YEARS`` 年前にする。"""
        if warmup_first_day is None:
            warmup_first_day = _years_before(train_first_day, DEFAULT_WARMUP_YEARS)
        return cls(warmup_first_day, train_first_day, valid_first_day, test_first_day)

    @classmethod
    def default(cls) -> TrainingPeriod:
        """既定の期間（設計書 08 の 3）。"""
        return cls(DEFAULT_WARMUP_FIRST_DAY, DEFAULT_TRAIN_FIRST_DAY,
                   DEFAULT_VALID_FIRST_DAY, DEFAULT_TEST_FIRST_DAY)

    def boundaries(self) -> dict[str, date]:
        """区切りの名前 → 日（古い順）。"""
        return {
            "ウォームアップの始まり": self.warmup_first_day, "学習データの始まり": self.train_first_day,
            "検証データの始まり": self.valid_first_day, "テストデータの始まり": self.test_first_day,
        }


def _years_before(day: date, years: int) -> date:
    """``day`` の ``years`` 年前の同じ月日。2月29日で相手の年に無ければ 2月28日。"""
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)
