"""まとまり L（騎手・調教師・血統の市場に対する成績）の作り方。

DB を使わず、手で作った記録を渡して確かめる。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import pytest

from ..feature import BASE_FEATURES, MARKET_FEATURES, PEOPLE_MARKET_FEATURES, EntryRecords, FeatureCatalog, WorkoutCoverage
from ..feature.group import PEOPLE_MARKET_COLUMNS, PeopleMarketFeatures
from ..feature.history import MarketExcessRate

RACE_DAY = date(2024, 6, 1)
_JOCKEY = PEOPLE_MARKET_COLUMNS["jockey_code"]


def _entry(jockey: str | None = "J1", trainer: str = "T1", sire: str = "S1", damsire: str = "D1") -> dict[str, Any]:
    """出走の行1行。まとまり L が読む列だけを入れる。"""
    return {"race_date": pd.Timestamp(RACE_DAY), "jockey_code": jockey, "trainer_code": trainer,
            "sire": sire, "damsire": damsire}


def _race(days_before: int, odds: list[float], finishes: list[int], jockeys: list[str]) -> list[dict[str, Any]]:
    """過去の1レースの全頭。調教師・血統は、どの馬も騎手と同じ名前にしておく。"""
    race_date = pd.Timestamp(RACE_DAY - timedelta(days=days_before))
    return [{"race_id": f"r{days_before}", "race_date": race_date, "win_odds": odd, "finish": finish,
             "jockey_code": jockey, "trainer_code": jockey, "sire": jockey, "damsire": jockey}
            for odd, finish, jockey in zip(odds, finishes, jockeys)]


def _build(entries: list[dict[str, Any]], runs: list[dict[str, Any]]) -> pd.DataFrame:
    records = EntryRecords(
        entries=pd.DataFrame(entries), past_runs=pd.DataFrame(), workouts=pd.DataFrame(),
        workout_coverage=WorkoutCoverage.complete(), jockey_days=pd.DataFrame(), trainer_days=pd.DataFrame(),
        sire_days=pd.DataFrame(), damsire_days=pd.DataFrame(), market_runs=pd.DataFrame(runs),
    )
    return PeopleMarketFeatures().build(records)


def test_the_four_features_are_numbers_in_group_l_known_from_thursday():
    assert [feature.name for feature in PEOPLE_MARKET_FEATURES] == list(PEOPLE_MARKET_COLUMNS.values())
    assert all(feature.group == "L" and not feature.is_categorical for feature in PEOPLE_MARKET_FEATURES)
    # 木曜から分かる（過去のレースのオッズだけを使う）
    assert all(feature.known_from.value == "thursday" for feature in PEOPLE_MARKET_FEATURES)
    # 全頭の予想の一覧（A〜J）に足しても名前が重ならない
    assert len(FeatureCatalog(BASE_FEATURES + MARKET_FEATURES + PEOPLE_MARKET_FEATURES).names) == 79


def test_excess_is_places_minus_market_expectation_shrunk_by_fifty_starts():
    # 3頭立て（3頭とも3着以内）なので、オッズから見た3着以内率はどの馬も 1。J1 は2回とも3着以内 → 超過 0
    # 4頭立ての等しいオッズでは、どの馬もオッズから見た3着以内率 0.75。J1 が3着以内 → 1 − 0.75 = 0.25
    runs = _race(10, [3.0, 3.0, 3.0, 3.0], [1, 2, 3, 4], ["J1", "J2", "J3", "J4"])
    features = _build([_entry("J1"), _entry("J4")], runs)
    assert features[_JOCKEY].tolist() == pytest.approx([0.25 / 51, -0.75 / 51])


def test_only_the_365_days_until_the_day_before_are_counted():
    runs = [
        *_race(0, [3.0, 3.0, 3.0, 3.0], [1, 2, 3, 4], ["J1", "J2", "J3", "J4"]),      # 当日: 数えない
        *_race(366, [3.0, 3.0, 3.0, 3.0], [1, 2, 3, 4], ["J1", "J2", "J3", "J4"]),    # 366日前: 数えない
        *_race(365, [3.0, 3.0, 3.0, 3.0], [4, 2, 3, 1], ["J1", "J2", "J3", "J4"]),    # 365日前: 数える
    ]
    features = _build([_entry("J1")], runs)
    assert features[_JOCKEY].tolist() == pytest.approx([-0.75 / 51])


def test_no_history_is_zero_and_missing_key_is_missing():
    runs = _race(10, [3.0, 3.0, 3.0, 3.0], [1, 2, 3, 4], ["J1", "J2", "J3", "J4"])
    features = _build([_entry("新人"), _entry(None)], runs)
    assert features[_JOCKEY].iloc[0] == 0.0
    assert pd.isna(features[_JOCKEY].iloc[1])


def test_each_column_counts_its_own_key():
    runs = _race(10, [3.0, 3.0, 3.0, 3.0], [1, 2, 3, 4], ["J1", "J2", "J3", "J4"])
    features = _build([_entry("J1", trainer="J4", sire="J2", damsire="J9")], runs)
    assert list(features.columns) == list(PEOPLE_MARKET_COLUMNS.values())
    assert features.iloc[0].tolist() == pytest.approx([0.25 / 51, -0.75 / 51, 0.25 / 51, 0.0])


def test_rate_keeps_the_entry_index():
    entries = pd.DataFrame([_entry("J1"), _entry("J2")], index=[7, 3])
    runs = pd.DataFrame(_race(10, [3.0, 3.0, 3.0, 3.0], [1, 2, 3, 4], ["J1", "J2", "J3", "J4"]))
    runs = runs.assign(placed=[1.0, 1.0, 1.0, 0.0], expected=[0.75] * 4)
    rate = MarketExcessRate(entries, "jockey_code").of(runs)
    assert rate.index.tolist() == [7, 3]
