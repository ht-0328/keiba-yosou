"""研究「能力指数の作り方」の物差しのテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 共通.ability import ABILITY, FIELD_LEVEL, FIGURE, RUNS_USED
from 能力指数の作り方.analysis import AccuracyBreakdown, EraRaceTable, FigureConsistency, IndexAccuracy


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


def test_年ごとの分け方は相関とクラスの間と中の広がりを出す() -> None:
    runs = _runs().assign(**{FIELD_LEVEL: ["未勝利・3歳"] * 3 + ["1勝クラス・古馬"] * 3, RUNS_USED: 8})
    score = AccuracyBreakdown().score(runs, "2020-01-01", "2020-12-31")
    chosen = runs[runs[ABILITY].notna()]
    assert score["走の数"] == 4 and score["1レースの頭数"] == pytest.approx(1.0)
    assert score["指数の広がり"] == pytest.approx(chosen[FIGURE].std())
    level_mean = chosen.groupby(FIELD_LEVEL)[FIGURE].transform("mean")
    assert score["クラスの間の広がり"] == pytest.approx(level_mean.std())
    assert score["クラスの中の広がり"] == pytest.approx((chosen[FIGURE] - level_mean).std())


def test_降級制度の廃止の後のレースだけ水準を分ける() -> None:
    runs = pd.DataFrame({
        "race_id": ["A", "B", "C"], "race_date": pd.to_datetime(["2019-05-26", "2019-06-01", "2019-06-01"]),
        "venue_code": "05", "track_code": "23", "surface": "芝", "distance_m": 1600, "condition": "良",
        "class_name": ["2勝クラス", "2勝クラス", "1勝クラス"], "first3f": 35.0, "last3f_race": 35.0,
        "age": 4, "finish": pd.array([1, 1, 1], dtype="Int64"), "finish_time": 95.0,
    })
    levels = EraRaceTable().build(runs).set_index("race_id")[FIELD_LEVEL]
    assert levels.to_dict() == {"A": "2勝クラス・古馬", "B": "2勝クラス・古馬・廃止後", "C": "1勝クラス・古馬"}
