"""能力指数の部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 共通.ability import (
    ABILITY,
    APTITUDE_COLUMNS,
    BASE,
    COURSE_STANDARD,
    DISTANCE,
    GOING,
    FIELD_LEVEL,
    FIGURE,
    HIGH,
    MEDIAN_LOG_TIME,
    PACE,
    SLOW,
    TRACK_VARIANT,
    AbilityIndex,
    AbilitySettings,
    PaceAdjustment,
    PaceBalance,
    RaceTable,
    SpeedFigure,
    SpeedStandard,
)


def _races(days: int = 40) -> pd.DataFrame:
    """2つのコース・2つの水準・日ごとの馬場差から作った、中央値タイムの対数。"""
    rows = []
    rng = np.random.default_rng(0)
    for day in range(days):
        variant = rng.normal(0, 0.5)
        for course, base in (("1600", 460.0), ("1200", 420.0)):
            for level, gap in (("1勝クラス・古馬", 0.0), ("未勝利・3歳", 1.0)):
                rows.append({"race_id": f"{day}-{course}-{level}", "race_date": pd.Timestamp("2024-01-06") + pd.Timedelta(days=7 * day),
                             "venue_code": "05", "track_code": "23", "distance_m": int(course), "surface": "芝",
                             FIELD_LEVEL: level, MEDIAN_LOG_TIME: base + gap + variant, "_variant": variant})
    return pd.DataFrame(rows)


def test_基準タイム_水準の差_馬場差に分けられる() -> None:
    races = _races()
    applied = SpeedStandard().fit(races, pd.Timestamp("2030-01-01")).apply(races)
    one = applied[(applied["distance_m"] == 1600) & (applied[FIELD_LEVEL] == "未勝利・3歳")]
    assert one["水準の差"].iloc[0] == pytest.approx(1.0, abs=1e-6)
    centered = races["_variant"] - races["_variant"].mean()
    assert applied[TRACK_VARIANT].to_numpy() == pytest.approx(centered.to_numpy(), abs=1e-6)


def test_レースの表は中央値タイムと年齢の組を持つ() -> None:
    runs = pd.DataFrame({
        "race_id": "A", "race_date": pd.Timestamp("2025-01-05"), "venue_code": "05", "track_code": "23", "surface": "芝",
        "distance_m": 1600, "condition": "良", "class_name": "未勝利", "first3f": 35.0, "last3f_race": 34.0,
        "age": [3, 3, 3], "finish": pd.array([1, 2, None], dtype="Int64"), "finish_time": [95.0, 96.0, 0.0],
    })
    races = RaceTable().build(runs)
    assert races[FIELD_LEVEL].iloc[0] == "未勝利・3歳"
    assert races[MEDIAN_LOG_TIME].iloc[0] == pytest.approx(100 * np.log(95.5))


def _figure_runs() -> pd.DataFrame:
    return pd.DataFrame({
        "race_id": ["A", "A", "A"], "finish": pd.array([1, 2, 3], dtype="Int64"), "finish_time": [95.0, 95.0, 110.0],
        "carried": [55.0, 57.0, 55.0], COURSE_STANDARD: 100 * np.log(96.0), TRACK_VARIANT: 0.0,
        "style": ["逃げ", "差し", "追込"], PACE: [SLOW, SLOW, SLOW],
    })


def test_スピード指数は重い斤量ほど高く_ペース補正の分を引く() -> None:
    offsets = pd.Series({("逃げ", SLOW): 0.3})
    figure = SpeedFigure(0.15, offsets).build(_figure_runs())[FIGURE]
    plain = 80 + 10 * (100 * np.log(96.0) - 100 * np.log(95.0))
    assert figure.iloc[1] - figure.iloc[0] == pytest.approx(10 * (0.15 * 2 + 0.3))
    assert figure.iloc[0] == pytest.approx(plain - 3.0)


def test_大きく負けた走は切り上げる() -> None:
    figure = SpeedFigure(0.0, floor_gap=30.0).build(_figure_runs())[FIGURE]
    assert figure.iloc[2] == pytest.approx(figure.iloc[0] - 30.0)


def test_ペースは前後半の差を基準と比べて分ける() -> None:
    count = 40
    races = pd.DataFrame({"venue_code": "05", "track_code": "23", "distance_m": 1600, "condition": "良",
                          "first3f": 35.0 + np.tile([-0.5, 0.5], count // 2), "last3f_race": 35.0})
    balance = PaceBalance().fit(races)
    probe = pd.DataFrame({"venue_code": "05", "track_code": "23", "distance_m": 1600, "condition": ["良", "不良"],
                          "first3f": [34.0, 36.0], "last3f_race": 35.0})
    assert balance.band(probe).tolist() == [HIGH, SLOW]


def test_ペース補正の大きさは同じ馬のふだんとの差で測る() -> None:
    runs = pd.DataFrame({"horse_id": ["H"] * 4, "style": ["逃げ"] * 4, PACE: [SLOW, SLOW, HIGH, HIGH],
                         FIGURE: [83.0, 83.0, 77.0, 77.0]})
    offsets = PaceAdjustment().fit(runs)
    assert offsets[("逃げ", SLOW)] == pytest.approx(0.3)


def _history() -> pd.DataFrame:
    """1頭の馬の、古い順の4走（最後は今回で、結果はまだ無い）。"""
    return pd.DataFrame({
        "race_id": ["R1", "R2", "R3", "R4"], "horse_id": "H1",
        "race_date": pd.to_datetime(["2025-01-05", "2025-02-05", "2025-03-05", "2025-04-05"]),
        "distance_m": [1600, 2000, 1600, 1600], "surface": ["芝", "芝", "ダート", "芝"], "venue_code": ["05", "06", "05", "05"],
        "condition": ["良", "良", "良", "良"], FIGURE: [90.0, 80.0, 50.0, np.nan],
    })


def test_基礎の速さは前の走だけを新しさで重み付けして平均する() -> None:
    index = AbilityIndex(AbilitySettings(recency=0.5)).build(_history())
    assert np.isnan(index[BASE].iloc[0])
    assert index[BASE].iloc[3] == pytest.approx((50 * 1 + 80 * 0.5 + 90 * 0.25) / 1.75)


def test_馬場の適性は芝ダの違う走を軽く見た平均と基礎の速さの差() -> None:
    settings = AbilitySettings(recency=1.0, other_surface=0.4, aptitudes=(GOING,))
    index = AbilityIndex(settings).build(_history())
    expected = (50 * 0.4 + 80 + 90) / 2.4
    assert index[APTITUDE_COLUMNS[GOING]].iloc[3] == pytest.approx(expected - (50 + 80 + 90) / 3)
    assert index[ABILITY].iloc[3] == pytest.approx(expected)


def test_距離の近い走ほど重く見る() -> None:
    settings = AbilitySettings(recency=1.0, distance_scale=800.0, other_surface=1.0, aptitudes=(DISTANCE,))
    index = AbilityIndex(settings).build(_history())
    far = np.exp(-400 / 800)
    assert index[ABILITY].iloc[3] == pytest.approx((50 + 80 * far + 90) / (2 + far))
