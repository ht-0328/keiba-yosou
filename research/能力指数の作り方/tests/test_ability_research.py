"""研究「能力指数の作り方」の物差しのテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 共通.ability import ABILITY, FIGURE
from 能力指数の作り方.analysis import FigureConsistency, IndexAccuracy


def _runs() -> pd.DataFrame:
    return pd.DataFrame({
        "race_id": ["A1", "A2", "A3", "B1", "B2", "B3"], "horse_id": ["A"] * 3 + ["B"] * 3,
        "race_date": pd.to_datetime(["2020-01-05", "2020-02-05", "2020-03-05"] * 2),
        FIGURE: [80.0, 82.0, 84.0, 60.0, 61.0, 63.0], ABILITY: [None, 80.0, 81.0, None, 60.0, 60.5],
    })


def test_続けた走の相関は同じ馬の1つ前の走と比べる() -> None:
    score = FigureConsistency().score(_runs(), "2020-01-01", "2020-12-31")
    assert score["組の数"] == 4
    assert score["続けた走の相関"] == pytest.approx(pd.Series([82.0, 84.0, 61.0, 63.0]).corr(pd.Series([80.0, 82.0, 60.0, 61.0])))


def test_能力指数の当たり具合は指数の付いた走だけで比べる() -> None:
    score = IndexAccuracy().score(_runs(), "2020-01-01", "2020-12-31")
    assert score["走の数"] == 4 and score["付いた割合"] == pytest.approx(4 / 6 * 100)
    assert score["ずれ"] == pytest.approx((2 + 3 + 1 + 2.5) / 4)
