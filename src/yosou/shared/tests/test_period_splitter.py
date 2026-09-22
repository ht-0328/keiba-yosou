"""学習データの期間（4つの区切りの日）と、時期で3つに分けること。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ..dataset import RACE_DATE, PeriodSplitter, TrainingData, TrainingPeriod
from ..feature import Feature, FeatureCatalog, FeatureKind

PERIOD = TrainingPeriod(date(2023, 1, 1), date(2024, 1, 1), date(2025, 7, 1), date(2026, 1, 1))
#: このテストの学習データ（特徴量は斤量だけ、目的変数は1つ）。
CATALOG = FeatureCatalog((Feature("斤量", "B", FeatureKind.NUMERIC),))
LABEL_NAME = "目的変数"


def _data(days: list[str]) -> TrainingData:
    index = pd.RangeIndex(len(days))
    return TrainingData(
        ids=pd.DataFrame({RACE_DATE: pd.to_datetime(days)}, index=index),
        features=pd.DataFrame({"斤量": [55.0] * len(days)}, index=index),
        targets=pd.DataFrame({LABEL_NAME: [1] * len(days)}, index=index),
        evaluation=pd.DataFrame(index=index),
        catalog=CATALOG,
        label_name=LABEL_NAME,
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


@pytest.mark.parametrize(("train_first_day", "warmup_first_day"), [
    (date(2021, 8, 1), date(2020, 1, 1)), (date(2024, 1, 1), date(2023, 1, 1)), (date(2024, 2, 29), date(2023, 1, 1)),
])
def test_warmup_defaults_to_january_of_the_previous_year(train_first_day: date, warmup_first_day: date):
    period = TrainingPeriod.starting(train_first_day, date(2025, 7, 1), date(2026, 1, 1))
    assert period.warmup_first_day == warmup_first_day


def test_given_warmup_is_kept():
    given = TrainingPeriod.starting(date(2021, 8, 1), date(2025, 7, 1), date(2026, 1, 1),
                                    warmup_first_day=date(2021, 1, 1))
    assert given.warmup_first_day == date(2021, 1, 1)


def test_default_period_matches_the_design():
    # 設計書 08 の 4: 学習は 2021年8月から、ウォームアップは 2020年
    expected = TrainingPeriod(date(2020, 1, 1), date(2021, 8, 1), date(2025, 7, 1), date(2026, 1, 1))
    assert TrainingPeriod.default() == expected
