"""1つの組の、1つの年の学習・検証・予測の期間。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class YearPeriod:
    """1つの組の、1つの年の期間。どれも「この日から、次の区切りの前日まで」。"""

    train_first_day: date
    valid_first_day: date
    predict_first_day: date
    predict_end_day: date
