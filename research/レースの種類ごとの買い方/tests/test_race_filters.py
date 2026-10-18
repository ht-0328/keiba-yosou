"""手順5（券種ごとに向くレースで絞る案）の部品のテスト。値は架空で、DB は使わない。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from レースの種類ごとの買い方.analysis import filter_selector
from レースの種類ごとの買い方.analysis.buy_rule import BuyRule
from レースの種類ごとの買い方.analysis.filter_selector import FilterSelector
from レースの種類ごとの買い方.analysis.race_filter import RaceFilter
from レースの種類ごとの買い方.analysis.race_traits import RaceTraits
from レースの種類ごとの買い方.analysis.rule_day_table import HIT_RACES, PAYOUT, POINTS, RACES
from レースの種類ごとの買い方.analysis.trait_bins import TraitBins


def test_レースの中身は人気の偏りと食い違いから作る() -> None:
    marked = pd.DataFrame({"race_id": ["r"] * 4, "win_odds": [1.8, 4.0, 8.0, 20.0], "market_win": [0.4, 0.2, 0.1, 0.3],
                           "win_probability": [0.3, 0.3, 0.1, 0.3], "field_size": [4] * 4, "mark": ["◎", "○", "", ""],
                           "win_value": [0.9, 1.1, 0.5, 0.7], "is_danger": [False, True, False, False]})
    row = RaceTraits().of(marked).iloc[0]
    assert row["favorite_odds"] == 1.8 and row["top3_share"] == pytest.approx(0.9) and row["model_gap"] == pytest.approx(0.1)
    assert row["top_value"] == 0.9 and row["has_danger"] == 1.0


def _traits(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"race_id": [str(at) for at in range(len(values))], "favorite_odds": values, "top3_share": values,
                         "field_size": values, "model_gap": values, "top_value": values, "has_danger": [0.0] * len(values)})


def test_帯は決めた期間の5分位で分け_区切りちょうどは上の帯() -> None:
    bins = TraitBins(_traits([float(at) for at in range(1, 11)]))
    edges = bins.edges("favorite_odds")
    assert len(edges) == 4 and bins.labels("favorite_odds") == ["0", "1", "2", "3", "4"]
    labels = bins.of(_traits([0.5, float(edges[0]), 100.0]))["bin_favorite_odds"].tolist()
    assert labels == ["0", "1", "4"]
    assert bins.labels("has_danger") == ["0", "1"]


def test_絞り方は下限と上限の両端を含む() -> None:
    traits = _traits([1.5, 1.9, 2.9, 3.0])
    assert RaceFilter("favorite_odds", None, 1.9, "").passes(traits).tolist() == [True, True, False, False]
    assert RaceFilter("favorite_odds", 2.9, None, "").passes(traits).tolist() == [False, False, True, True]


def test_決まりと絞り方は前の年だけで回収率の下の端で選ぶ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(filter_selector, "MIN_HITS", 30)
    days = pd.DatetimeIndex([pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=at) for year in (2016, 2017, 2018) for at in range(60)])
    # 中身1つ・帯2つ・決まり2つ。決まり0 は帯1 だけで毎日 3倍が当たり、帯0 は毎日外れる。決まり1 はどちらの帯も毎日外れる。
    table = np.zeros((2, 2, len(days), 4))
    table[:, :, :, POINTS] = 1.0
    table[:, :, :, RACES] = 1.0
    table[0, 1, :, PAYOUT], table[0, 1, :, HIT_RACES] = 300.0, 1.0
    table[1, :, ::2, HIT_RACES] = 1.0
    rules = [BuyRule("全", 1.0, 300, 0), BuyRule("全", 1.5, 300, 0)]
    selector = FilterSelector({"favorite_odds": table}, days, rules)
    choice, cells = selector.choose(2018)
    assert choice.rule == rules[0] and choice.filter_text == "favorite_odds の帯 2 以上"
    assert cells[days.year == 2018, PAYOUT].sum() == 300.0 * 60
