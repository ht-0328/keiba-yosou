"""レースの回顧（``RaceReviews``）の、予想のペースの付け方のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from yosou.review import names
from yosou.review.race_reviews import RaceReviews


def test_予想のペースは予想のあるレースだけ一番高いものを付け_無いレースは空のまま() -> None:
    table = pd.DataFrame({names.RACE_ID: ["r1", "r2", "r3"], names.FORECAST_PACE: None,
                          names.FORECAST_HIGH: float("nan"), names.FORECAST_SLOW: float("nan")})
    paces = pd.DataFrame({names.RACE_ID: ["r1", "r3"], names.FORECAST_HIGH: [0.6, 0.1], names.FORECAST_SLOW: [0.1, 0.7]})
    reviewed = RaceReviews()._with_forecasts(table, paces).set_index(names.RACE_ID)
    assert reviewed.loc["r1", names.FORECAST_PACE] == "ハイ" and reviewed.loc["r3", names.FORECAST_PACE] == "スロー"
    assert pd.isna(reviewed.loc["r2", names.FORECAST_PACE]) and pd.isna(reviewed.loc["r2", names.FORECAST_HIGH])


def test_予想のあるレースが1つも無くても止まらない() -> None:
    table = pd.DataFrame({names.RACE_ID: ["r1"], names.FORECAST_PACE: None, names.FORECAST_HIGH: float("nan"), names.FORECAST_SLOW: float("nan")})
    paces = pd.DataFrame({names.RACE_ID: ["x"], names.FORECAST_HIGH: [0.5], names.FORECAST_SLOW: [0.2]})
    assert RaceReviews()._with_forecasts(table, paces)[names.FORECAST_PACE].isna().all()
