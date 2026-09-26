"""前半タイムの基準の作り方（設計書 06 の図2a・10 の 5.）を、小さな表で確かめる。"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ..feature.history import MEAN, STAGE, PaceBaseline
from ..feature.history.pace_baseline import MERGED_CLASS, MIN_RACES, NO_BASELINE, SAME_CLASS


def _races(count: int, class_order: int, first: date, time: float) -> pd.DataFrame:
    """同じコース・同じクラスで、1週ごとに行われたレース。"""
    return pd.DataFrame({
        "race_date": [first + timedelta(days=7 * week) for week in range(count)],
        "venue_code": "05", "track_code": "11", "distance_m": 1600, "class_order": class_order,
        "first3f": [time + (0.5 if week % 2 else -0.5) for week in range(count)],
    })


def test_same_class_baseline_counts_only_earlier_days() -> None:
    races = _races(MIN_RACES + 1, 3, date(2020, 1, 4), 35.0)
    attached = PaceBaseline("first3f", "基準").attach(races)
    last = attached.iloc[-1]
    assert last["基準" + STAGE] == SAME_CLASS
    assert np.isclose(last["基準" + MEAN], races["first3f"].iloc[:-1].mean())
    assert attached.iloc[0]["基準" + STAGE] == NO_BASELINE


def test_same_day_races_are_not_counted() -> None:
    races = _races(MIN_RACES + 1, 3, date(2020, 1, 4), 35.0)
    same_day = races.iloc[[-1]].assign(first3f=99.0)
    attached = PaceBaseline("first3f", "基準").attach(pd.concat([races, same_day], ignore_index=True))
    assert attached["基準" + MEAN].notna().iloc[-1]
    assert attached["基準" + MEAN].iloc[-1] == attached["基準" + MEAN].iloc[-2]


def test_classes_are_merged_when_one_class_is_short() -> None:
    many = _races(MIN_RACES, 3, date(2020, 1, 4), 35.0)
    target = _races(1, 5, date(2020, 1, 4) + timedelta(days=7 * MIN_RACES), 34.0)
    attached = PaceBaseline("first3f", "基準").attach(pd.concat([many, target], ignore_index=True))
    assert attached.iloc[-1]["基準" + STAGE] == MERGED_CLASS
