"""まとまり M（馬の力の材料）の部品の作り方。DB を使わず、手で作った表を渡して確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..feature import ABILITY_FEATURES
from ..feature.ability import ability_columns
from ..feature.ability.ability_columns import PLACE_PRIOR, RELATIVE_COLUMNS, WIN_PRIOR
from ..feature.ability.cumulative_record_rates import CumulativeRecordRates
from ..feature.ability.race_pace import RacePace
from ..feature.ability.race_relative_columns import RaceRelativeColumns
from ..feature.ability.sale_price_columns import SalePriceColumns
from ..feature.ability.speed_figure_history import SpeedFigureHistory


def test_there_are_197_research_features_and_5_sale_features():
    names = ability_columns()
    assert len(names) == len(set(names)) == 202 and [feature.name for feature in ABILITY_FEATURES] == list(names)
    # 前日から分かるのは枠番・馬番・馬場状態を使う7個、当日からは馬体重を使う3個
    timings = pd.Series([feature.known_from.value for feature in ABILITY_FEATURES]).value_counts()
    assert timings.to_dict() == {"thursday": 192, "day_before": 7, "race_day": 3}


def _runs(rows: list[tuple[str, str, str, float]]) -> pd.DataFrame:
    """（レースID, 開催日, 騎手, 着順）の並びから、出走の表を作る。馬はレースごとに別。"""
    return pd.DataFrame([{"race_id": race, "horse_id": f"{race}-{jockey}", "race_date": pd.Timestamp(day),
                          "jockey_code": jockey, "finish": finish} for race, day, jockey, finish in rows])


def test_record_rates_count_only_the_days_before():
    runs = _runs([("r1", "2024-01-06", "J1", 1), ("r2", "2024-01-07", "J1", 1), ("r3", "2024-01-07", "J1", 5),
                  ("r4", "2024-01-13", "J1", 2)])
    rates = CumulativeRecordRates().build(runs, ("jockey_code",), "騎手").set_index("race_id")
    # 初めての日は全体の値。同じ日のレース（r2・r3）は、その日の結果を数えない
    assert rates.loc["r1", "騎手_勝率"] == pytest.approx(WIN_PRIOR)
    assert rates.loc["r2", "騎手_勝率"] == rates.loc["r3", "騎手_勝率"] == pytest.approx((1 + 100 * WIN_PRIOR) / 101)
    assert rates.loc["r4", "騎手_3着内率"] == pytest.approx((2 + 100 * PLACE_PRIOR) / 103)
    assert rates.loc["r4", "騎手_出走数"] == 3


def test_race_pace_needs_twenty_earlier_races_of_the_same_condition():
    days = pd.date_range("2024-01-01", periods=22, freq="D")
    first3f = [35.0 + (index % 2) * 0.4 for index in range(21)] + [34.0]
    runs = pd.DataFrame({"race_id": [f"r{index}" for index in range(22)], "race_date": days, "venue_code": "05",
                         "surface": "芝", "distance_m": 1600, "condition": "良", "first3f": first3f})
    pace = RacePace().of(runs)
    assert np.isnan(pace["r19"]) and pace["r21"] > 2.0


def test_race_relative_columns_compare_with_the_same_race():
    table = pd.DataFrame({"race_id": ["r1"] * 3, **{column: [1.0, 2.0, 3.0] for column in RELATIVE_COLUMNS}})
    relative = RaceRelativeColumns().build(table)
    # 大きいほど良い列（指数）は大きい順、小さいほど良い列（斤量）は小さい順
    assert relative["指数_前走_順位"].tolist() == [3.0, 2.0, 1.0]
    assert relative["carried_順位"].tolist() == [1.0, 2.0, 3.0]
    assert relative["指数_前走_最良との差"].tolist() == [-2.0, -1.0, 0.0]


def test_sale_price_uses_the_latest_sale_before_the_race():
    table = pd.DataFrame({"race_id": ["r1", "r1"], "horse_id": ["h1", "h2"],
                          "race_date": [pd.Timestamp("2024-06-01")] * 2})
    sales = pd.DataFrame({"horse_id": ["h1", "h1", "h1"], "price": [1_000_000, 10_000_000, 99_000_000],
                          "sale_age": [0, 1, 2],
                          "sale_end": pd.to_datetime(["2022-07-01", "2023-07-01", "2024-07-01"])})
    columns = SalePriceColumns().build(table, sales)
    # レースの後のセリ（2024-07-01）は使わない。買われていない馬は価格が欠損値で「買われた」が 0
    assert columns.loc[0, "セリの価格（log）"] == pytest.approx(7.0) and columns.loc[0, "セリの時の年齢"] == 1
    assert np.isnan(columns.loc[1, "セリの価格（log）"]) and columns.loc[1, "セリで買われた"] == 0


def test_speed_figures_use_only_earlier_runs():
    figures = pd.DataFrame({
        "race_id": ["a", "b", "c"], "horse_id": ["h1"] * 3,
        "race_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]), "venue_code": "05", "surface": "芝",
        "distance_m": 1600, "condition": "良", "finish": [3, 1, np.nan], "figure": [70.0, 80.0, np.nan],
    })
    history = SpeedFigureHistory().build(figures).set_index("race_id")
    # これから走るレース（c）の値は、前の2走だけから作る
    assert history.loc["c", "指数_前走"] == 80.0 and history.loc["c", "指数_近3走の平均"] == 75.0
    assert history.loc["c", "指数_新しさの重み"] == pytest.approx((80 + 70 * 0.7) / 1.7)
    assert history.loc["c", "出走数"] == 2 and np.isnan(history.loc["a", "指数_前走"])
