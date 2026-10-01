"""複勝の見込みの倍率（最低オッズの帯と、オッズの幅での直し。穴馬の設計書 15 の 18）。手で作った値だけで確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..place_value import BANDS, PlacePriceEstimator
from ..place_value.place_price_estimator import SPREAD_BANDS


def _bets() -> tuple[pd.Series, pd.Series, pd.Series]:
    """最低オッズ 4.0 倍の当たり4点。幅の狭い（1.3 倍）2点は 4.0 倍の払戻、幅の広い（3.0 倍）2点は 6.0 倍の払戻。"""
    lowest = pd.Series([4.0, 4.0, 4.0, 4.0, 4.0])
    highest = pd.Series([5.2, 5.2, 12.0, 12.0, 12.0])
    payout = pd.Series([400.0, 400.0, 600.0, 600.0, 0.0])
    return lowest, payout, highest


def test_without_the_highest_odds_the_estimate_uses_only_the_lowest_odds_band():
    lowest, payout, highest = _bets()
    estimator = PlacePriceEstimator().fit(lowest, payout)
    # 帯の倍率は当たり4点の 払戻 ÷ 最低オッズ の平均 1.25。最高オッズを渡しても、幅では直さない
    assert estimator.estimate(pd.Series([4.0])).iloc[0] == pytest.approx(5.0)
    assert estimator.estimate(pd.Series([4.0]), pd.Series([5.2])).iloc[0] == pytest.approx(5.0)
    assert estimator.spread_multipliers() == {} and "spread_factors" not in estimator.state()


def test_the_spread_lowers_narrow_horses_and_raises_wide_horses():
    lowest, payout, highest = _bets()
    estimator = PlacePriceEstimator().fit(lowest, payout, highest)
    narrow, wide = estimator.estimate(pd.Series([4.0, 4.0]), pd.Series([5.2, 12.0]))
    # 幅の狭い帯の倍率は 1.0 ÷ 1.25 = 0.8、広い帯は 1.5 ÷ 1.25 = 1.2。見込みは実際の払戻に合う
    assert narrow == pytest.approx(4.0) and wide == pytest.approx(6.0)
    # 最高オッズの無い馬と、当たりの無かった幅の帯は直さない
    missing, empty_band = estimator.estimate(pd.Series([4.0, 4.0]), pd.Series([np.nan, 6.4]))
    assert missing == pytest.approx(5.0) and empty_band == pytest.approx(5.0)


def test_the_state_round_trips_and_old_states_still_load():
    lowest, payout, highest = _bets()
    estimator = PlacePriceEstimator().fit(lowest, payout, highest)
    state = estimator.state()
    assert state["spread_bands"] == list(SPREAD_BANDS) and len(state["spread_factors"]) == len(SPREAD_BANDS) - 1
    restored = PlacePriceEstimator.from_state(state)
    np.testing.assert_allclose(restored.estimate(pd.Series([4.0]), pd.Series([12.0])),
                               estimator.estimate(pd.Series([4.0]), pd.Series([12.0])))
    # 幅の倍率の無い前の版の形も読めて、幅では直さない
    old = PlacePriceEstimator.from_state({"bands": list(BANDS), "factors": [1.2] * (len(BANDS) - 1)})
    assert old.estimate(pd.Series([4.0]), pd.Series([12.0])).iloc[0] == pytest.approx(4.8)
    with pytest.raises(ValueError, match="幅の帯"):
        PlacePriceEstimator.from_state({**state, "spread_bands": [1.0, 2.0, 1e9]})
