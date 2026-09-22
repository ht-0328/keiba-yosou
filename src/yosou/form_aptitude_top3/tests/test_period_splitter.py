"""学習データの期間（4つの区切りの日）と、時期で3つに分けること。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ..dataset import RACE_DATE, TOP3, PeriodSplitter, TrainingData, TrainingPeriod

PERIOD = TrainingPeriod(date(2023, 1, 1), date(2024, 1, 1), date(2025, 7, 1), date(2026, 1, 1))


def _data(days: list[str]) -> TrainingData:
    index = pd.RangeIndex(len(days))
    return TrainingData(
        ids=pd.DataFrame({RACE_DATE: pd.to_datetime(days)}, index=index),
        features=pd.DataFrame({"斤量": [55.0] * len(days)}, index=index),
        targets=pd.DataFrame({TOP3: [1] * len(days)}, index=index),
        evaluation=pd.DataFrame(index=index),
    )


def test_split_uses_first_days_as_boundaries():
    data = _data(["2025-06-30", "2025-07-01", "2025-12-31", "2026-01-01"])
    split = PeriodSplitter(PERIOD).split(data)
    assert split.train.ids[RACE_DATE].tolist() == [pd.Timestamp("2025-06-30")]
    assert split.valid.ids[RACE_DATE].tolist() == [pd.Timestamp("2025-07-01"), pd.Timestamp("2025-12-31")]
    assert split.test.ids[RACE_DATE].tolist() == [pd.Timestamp("2026-01-01")]
    assert len(split.valid.features) == len(split.valid.targets) == 2


def test_empty_part_is_an_error():
    with pytest.raises(ValueError, match="テストデータが空"):
        PeriodSplitter(PERIOD).split(_data(["2025-06-30", "2025-07-01"]))


def test_boundaries_must_be_in_order():
    with pytest.raises(ValueError, match="検証データの始まり"):
        TrainingPeriod(date(2023, 1, 1), date(2024, 1, 1), date(2026, 1, 1), date(2025, 7, 1))
    with pytest.raises(ValueError, match="ウォームアップの始まり"):
        TrainingPeriod(date(2024, 1, 1), date(2024, 1, 1), date(2025, 7, 1), date(2026, 1, 1))


def test_warmup_defaults_to_one_year_before_the_training_data():
    period = TrainingPeriod.starting(date(2021, 8, 1), date(2025, 7, 1), date(2026, 1, 1))
    assert period.warmup_first_day == date(2020, 8, 1)
    # 2月29日の1年前は 2月28日
    leap = TrainingPeriod.starting(date(2024, 2, 29), date(2025, 7, 1), date(2026, 1, 1))
    assert leap.warmup_first_day == date(2023, 2, 28)
    # 書いた日はそのまま
    given = TrainingPeriod.starting(date(2021, 8, 1), date(2025, 7, 1), date(2026, 1, 1),
                                    warmup_first_day=date(2020, 1, 1))
    assert given.warmup_first_day == date(2020, 1, 1)


def test_default_period_matches_the_design():
    assert TrainingPeriod.default() == PERIOD
