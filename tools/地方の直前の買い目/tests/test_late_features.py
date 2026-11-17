"""LateFeatures（材料の表 → 特徴量）のテスト。"""

from __future__ import annotations

import numpy as np
import pytest

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_features import LateFeatures

from 地方の直前の買い目.testing.late_samples import material


def test_市場の見立てはレースの中で合計1_人気順はオッズの低い順() -> None:
    features = LateFeatures().build(material(races=2))
    assert features.groupby(c.RACE_ID)["mkt"].sum().round(9).tolist() == [1.0, 1.0]
    first = features[features[c.RACE_ID] == features[c.RACE_ID].iloc[0]]
    assert first.sort_values(c.ODDS_NOW)["rank"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert list(LateFeatures.matrix(features).columns) == list(c.FEATURES)


def test_動きは今と前の断面の対数の差_前の断面が無ければ欠損() -> None:
    table = material()
    table.loc[0, c.ODDS_A] = np.nan
    features = LateFeatures().build(table)
    assert np.isnan(features.loc[0, "mom_a"])
    assert features.loc[1, "mom_a"] == pytest.approx(np.log(1 / 1.1))
    assert features.loc[1, "mom_first"] == pytest.approx(np.log(1 / 0.9))


def test_競馬場とレース番号はレースID_から_曜日は開催日から() -> None:
    features = LateFeatures().build(material())
    assert features["venue"].iloc[0] == 44 and features["race_no"].iloc[0] == 1
    assert features["dow"].iloc[0] == 0   # 2024-01-01 は月曜


def test_今のオッズか当日の予想の無い馬は外し_残りで市場の見立てを作る() -> None:
    table = material()
    table.loc[0, c.ODDS_NOW] = 0.0
    table.loc[1, c.WIN_MODEL] = np.nan
    features = LateFeatures().build(table)
    assert features[c.HORSE_NO].tolist() == [3, 4, 5, 6]
    assert features["mkt"].sum() == pytest.approx(1.0) and features["p1_stn"].sum() == pytest.approx(1.0)


def test_列が足りなければ_ValueError() -> None:
    with pytest.raises(ValueError, match="odds_now"):
        LateFeatures().build(material().drop(columns=[c.ODDS_NOW]))
