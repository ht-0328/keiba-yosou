"""買い方の線と、確率のそろえ直しのテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 回収率100超.analysis.bet_rule import BetRule
from 回収率100超.analysis.ticket import RacePlaceProbability


def test_線以上の買い目だけを買う() -> None:
    selected = BetRule(lower=1.20).selects(pd.Series([1.19, 1.20, 1.50]))
    assert list(selected) == [False, True, True]


def test_期待値が欠けている買い目は買わない() -> None:
    selected = BetRule(lower=1.20).selects(pd.Series([float("nan"), 2.0]))
    assert list(selected) == [False, True]


def test_確率はレース内で対象頭数に合うようそろえ直す() -> None:
    probability = pd.Series([0.5, 0.5, 0.5, 0.5])          # 合計 2.0
    race = pd.Series(["R1"] * 4)
    places = pd.Series([3] * 4)
    scaled = RacePlaceProbability().normalize(probability, race, places)
    assert scaled.sum() == pytest.approx(3.0)


def test_少頭数のレースは2着までにそろえる() -> None:
    probability = pd.Series([0.4, 0.3, 0.2, 0.1, 0.5, 0.5])
    race = pd.Series(["R1"] * 5 + ["R2"])
    places = pd.Series([2] * 5 + [3])
    scaled = RacePlaceProbability().normalize(probability, race, places)
    assert scaled[:5].sum() == pytest.approx(2.0)


def test_そろえ直しても確率の大小は変わらない() -> None:
    probability = pd.Series([0.6, 0.3, 0.1])
    scaled = RacePlaceProbability().normalize(probability, pd.Series(["R1"] * 3), pd.Series([3] * 3))
    assert list(scaled.rank()) == list(probability.rank())


def test_確率が1を超えないように止める() -> None:
    probability = pd.Series([0.9, 0.05, 0.05])
    scaled = RacePlaceProbability().normalize(probability, pd.Series(["R1"] * 3), pd.Series([3] * 3))
    assert scaled.max() <= 1.0
