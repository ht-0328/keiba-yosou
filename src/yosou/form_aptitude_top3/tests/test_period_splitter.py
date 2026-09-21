"""学習データを時期で3つに分ける。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ..dataset import RACE_DATE, TOP3, PeriodSplitter, TrainingData


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
    split = PeriodSplitter(date(2025, 7, 1), date(2026, 1, 1)).split(data)
    assert split.train.ids[RACE_DATE].tolist() == [pd.Timestamp("2025-06-30")]
    assert split.valid.ids[RACE_DATE].tolist() == [pd.Timestamp("2025-07-01"), pd.Timestamp("2025-12-31")]
    assert split.test.ids[RACE_DATE].tolist() == [pd.Timestamp("2026-01-01")]
    assert len(split.valid.features) == len(split.valid.targets) == 2


def test_empty_part_is_an_error():
    with pytest.raises(ValueError, match="テストデータが空"):
        PeriodSplitter(date(2025, 7, 1), date(2026, 1, 1)).split(_data(["2025-06-30", "2025-07-01"]))


def test_boundaries_must_be_in_order():
    with pytest.raises(ValueError):
        PeriodSplitter(date(2026, 1, 1), date(2025, 7, 1))
