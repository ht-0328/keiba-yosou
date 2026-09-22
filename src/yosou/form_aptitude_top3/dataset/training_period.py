"""学習データの期間（4つの区切りの日）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: 既定の区切り（設計書 08 の 4）。学習データの始まりは、ウッドチップ調教の記録がそろう 2021年8月から。
DEFAULT_TRAIN_FIRST_DAY = date(2021, 8, 1)
DEFAULT_VALID_FIRST_DAY = date(2025, 7, 1)
DEFAULT_TEST_FIRST_DAY = date(2026, 1, 1)


@dataclass(frozen=True)
class TrainingPeriod:
    """学習データの期間を区切る4つの日（設計書 08 の 3・4）。古い順に並んでいなければ ``ValueError``。

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
        """``warmup_first_day`` を省略すると、学習データの始まりの前の年の1月1日にする（ウォームアップは1年以上）。"""
        if warmup_first_day is None:
            warmup_first_day = date(train_first_day.year - 1, 1, 1)
        return cls(warmup_first_day, train_first_day, valid_first_day, test_first_day)

    @classmethod
    def default(cls) -> TrainingPeriod:
        """既定の期間（設計書 08 の 4）。ウォームアップは 2020年1月から。"""
        return cls.starting(DEFAULT_TRAIN_FIRST_DAY, DEFAULT_VALID_FIRST_DAY, DEFAULT_TEST_FIRST_DAY)

    def boundaries(self) -> dict[str, date]:
        """区切りの名前 → 日（古い順）。"""
        return {
            "ウォームアップの始まり": self.warmup_first_day, "学習データの始まり": self.train_first_day,
            "検証データの始まり": self.valid_first_day, "テストデータの始まり": self.test_first_day,
        }
