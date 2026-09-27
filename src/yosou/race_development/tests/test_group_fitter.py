"""傾向 → 前半 → 後半 → 着順の組を、前の組の予測を足しながら学習して予測できるかを確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_ID

from ..feature import (
    CORNER4_PREDICTION,
    FAVORITE_OUT_PROBABILITY,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    TOP3_PROBABILITY,
    UPSET_BETS,
    WIN_PROBABILITY,
    PriorForecasts,
    big_upset_probability,
    calm_probability,
)
from ..feature.tendency_features import FAVORITE_OUT, TOP3
from ..workflow import ORDER_LAMBDA, DevelopmentModelKind


def test_tendency_forecasts_every_runner_and_every_race(forecasts) -> None:
    priors, _ = forecasts
    tendency = priors.tendency
    assert tendency.horses[TOP3_PROBABILITY].between(0, 1).all()
    for key in UPSET_BETS:
        total = tendency.races[calm_probability(key)] + tendency.races[big_upset_probability(key)]
        assert total.between(0, 1 + 1e-9).all()


def test_favorite_probability_is_only_for_favorites(forecasts) -> None:
    """人気馬の4着以下の確率は、人気馬にだけ付き、ほかの馬は欠損値になる。"""
    priors, _ = forecasts
    favorites = priors.tendency.horses[FAVORITE_OUT_PROBABILITY]
    assert favorites.notna().any()
    assert favorites.isna().any()


def test_runners_without_favorite_probability_stay_in_training_data(datasets, forecasts) -> None:
    """人気馬の確率が欠損値の馬（人気馬でない馬）も、前半の予想の学習データから外れない。"""
    priors, _ = forecasts
    data = datasets.of(DevelopmentModelKind.LEADER, PriorForecasts(priors.tendency))
    assert data.features[TOP3].notna().all()
    assert data.features[FAVORITE_OUT].isna().any()
    predicted_races = set(priors.tendency.horses[RACE_ID].astype(str))
    assert set(data.ids[RACE_ID].astype(str)) <= predicted_races


def test_early_probabilities_sum_to_one_per_race(forecasts) -> None:
    priors, _ = forecasts
    horses = priors.early.horses
    assert np.allclose(horses.groupby(RACE_ID)[LEADER_PROBABILITY].sum(), 1.0)
    assert horses[FRONT_PROBABILITY].between(0, 1).all()
    assert priors.early.races[HIGH_PROBABILITY].between(0, 1).all()
    quantiles = priors.early.races[list(FIRST_HALF_QUANTILES)].to_numpy()
    assert (np.diff(quantiles, axis=1) >= 0).all()


def test_late_and_finish_use_previous_forecasts(forecasts) -> None:
    priors, finish = forecasts
    assert priors.late.horses[CORNER4_PREDICTION].notna().all()
    assert np.allclose(finish.horses.groupby(RACE_ID)[WIN_PROBABILITY].sum(), 1.0)
    assert finish.horses[ORDER_LAMBDA].between(0.5, 1.0).all()


def test_every_kind_needs_the_tendency_forecast(datasets) -> None:
    """傾向の組の予測を渡さないと、どの予想の学習データも作れない（渡し忘れに気づけるように）。"""
    try:
        datasets.of(DevelopmentModelKind.LEADER, PriorForecasts())
    except ValueError as error:
        assert "既存の予想" in str(error)
    else:
        raise AssertionError("傾向の組の予測が無いのに、学習データを作れてしまった")


def test_tendency_part_is_empty_when_source_has_no_model_at_the_timing() -> None:
    """その時点で既存の予想がモデルを持たないとき（木曜の人気馬）は、列が全部欠損値になる。"""
    from ..feature import GroupForecast, TendencyFeatures
    ids = pd.DataFrame({RACE_ID: ["r1", "r1"], "馬ID": ["h1", "h2"]})
    tendency = GroupForecast(
        pd.DataFrame({RACE_ID: ["r1", "r1"], "馬ID": ["h1", "h2"], TOP3_PROBABILITY: [0.6, 0.2]}),
        pd.DataFrame({RACE_ID: ["r1"], **{calm_probability(key): [0.5] for key in UPSET_BETS},
                      **{big_upset_probability(key): [0.1] for key in UPSET_BETS}}),
    )
    features = TendencyFeatures().horse(ids, tendency)
    assert features[FAVORITE_OUT].isna().all()
    assert features[TOP3].tolist() == [0.6, 0.2]
    assert np.isclose(features["既存の予想の3着以内の確率の1位と2位の差"].iloc[0], 0.4)
