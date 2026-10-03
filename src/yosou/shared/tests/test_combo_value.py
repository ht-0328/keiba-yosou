"""組の期待値（``combo_value``）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..betting import TicketType
from ..combo_value import TOP3_RATIO, WIN_RATIO, ComboExpectedValue, HorseRatio


def _ratios() -> pd.DataFrame:
    """馬番 1〜4 の比。1番は 1着の比 1.3・3着以内の比 1.2、4番は市場の見立てが無い。"""
    table = HorseRatio().of(
        probability=pd.Series([0.60, 0.44, 0.30, 0.10], index=[1, 2, 3, 4]),
        market_top3=pd.Series([0.50, 0.40, 0.30, np.nan], index=[1, 2, 3, 4]),
        win_probability=pd.Series([0.26, 0.15, 0.08, 0.02], index=[1, 2, 3, 4]),
        market_win=pd.Series([0.20, 0.15, 0.10, 0.0], index=[1, 2, 3, 4]),
    )
    return table


def test_horse_ratio_is_model_over_market() -> None:
    ratios = _ratios()
    assert ratios.loc[1, WIN_RATIO] == pytest.approx(1.3) and ratios.loc[1, TOP3_RATIO] == pytest.approx(1.2)
    assert ratios.loc[2, WIN_RATIO] == pytest.approx(1.0) and ratios.loc[3, TOP3_RATIO] == pytest.approx(1.0)
    assert np.isnan(ratios.loc[4, WIN_RATIO]) and np.isnan(ratios.loc[4, TOP3_RATIO])  # 見立てが無い・0 なら欠損値


def test_trifecta_value_uses_the_win_ratio_for_first_place_and_drops_the_odds() -> None:
    values = ComboExpectedValue().of(TicketType.TRIFECTA, [(1, 2, 3), (2, 1, 3), (1, 2, 4)], _ratios())
    # 1着は1着の比、2・3着は3着以内の比: 0.725 × 1.3 × 1.1 × 1.0
    assert values[0] == pytest.approx(0.725 * 1.3 * 1.1 * 1.0)
    # 1着が 2番なら 0.725 × 1.0 × 1.2 × 1.0。同じ3頭でも並びで変わる
    assert values[1] == pytest.approx(0.725 * 1.0 * 1.2 * 1.0)
    assert np.isnan(values[2])  # 比の無い馬を含む組は欠損値


def test_trio_value_uses_the_top3_ratio_for_every_position() -> None:
    values = ComboExpectedValue().of(TicketType.TRIO, [(1, 2, 3)], _ratios())
    assert values[0] == pytest.approx(0.75 * 1.2 * 1.1 * 1.0)
    assert ComboExpectedValue().of(TicketType.TRIO, [], _ratios()).size == 0


def test_probability_is_value_over_odds() -> None:
    probability = ComboExpectedValue().probability(pd.Series([1.2, 0.9], index=[7, 8]), pd.Series([60.0, np.nan], index=[7, 8]))
    assert probability.loc[7] == pytest.approx(0.02) and np.isnan(probability.loc[8])
