"""学習の行づくりのテスト（払戻を付ける・外れの間引きと重み・モデルに渡す形）。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType
from yosou.shared.feature import PredictionTiming

from ..dataset import MISS_KEEP_RATES, ComboTableBuilder, HitLabeler, MissSampling, ModelDataFactory
from ..feature import CATALOGS
from . import synthetic_race as race

QUINELLA, TRIO = TicketType.QUINELLA, TicketType.TRIO


def _labeled(ticket_type: TicketType, payouts: pd.DataFrame) -> pd.DataFrame:
    table = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), race.boards())[ticket_type]
    race_dates = pd.Series({race.RACE: pd.Timestamp("2025-01-05")})
    return HitLabeler().label(ticket_type, table, payouts, race_dates)


def _many_rows(row_count: int, hit_count: int) -> pd.DataFrame:
    """当たり ``hit_count`` 行・外れ残りの、架空の組の表（間引きを確かめるのに要る列だけ）。"""
    return pd.DataFrame({"combo": np.arange(row_count), "hit": np.arange(row_count) < hit_count})


def test_払戻のある組が当たり_同じ組の払戻は合計する() -> None:
    payouts = pd.DataFrame({"race_id": race.RACE, "combo": ["0102", "0102", "0304"], "yen": [700, 500, 2_000]})
    labeled = _labeled(QUINELLA, payouts).set_index("combo")
    assert labeled.loc["0102", "payout"] == 1_200 and labeled.loc["0304", "payout"] == 2_000
    assert labeled["hit"].sum() == 2 and labeled.loc["0103", "payout"] == 0 and labeled.loc["0103", "hit"] == 0
    assert (labeled["race_date"] == pd.Timestamp("2025-01-05")).all()


def test_保存する列は_IDと評価用と目的変数と出発点と材料の順() -> None:
    labeled = _labeled(TRIO, pd.DataFrame({"race_id": [race.RACE], "combo": ["010203"], "yen": [900]}))
    head = ["race_id", "race_date", "ticket_type", "combo", "h1", "h2", "h3", "odds", "payout", "hit", "baseline"]
    assert list(labeled.columns) == [*head, *CATALOGS[TRIO].names]


def test_ほかのレースの払戻は付けない() -> None:
    payouts = pd.DataFrame({"race_id": ["2025010506010199"], "combo": ["0102"], "yen": [700]})
    assert _labeled(QUINELLA, payouts)["hit"].sum() == 0


def test_外れの間引きの割合は券種ごとに決まっている() -> None:
    rates = {ticket_type.label: rate for ticket_type, rate in MISS_KEEP_RATES.items()}
    assert rates == {"ワイド": 0.3, "馬連": 0.2, "馬単": 0.1, "3連複": 0.06, "3連単": 0.015}


def test_当たりは全部残し_外れは割合で間引いて重みを付ける() -> None:
    table = _many_rows(20_000, hit_count=100)
    sampled = MissSampling({QUINELLA: 0.1}).sample(QUINELLA, table, 2024)
    hits, misses = sampled[sampled["hit"]], sampled[~sampled["hit"]]
    assert len(hits) == 100 and (hits["weight"] == 1.0).all()
    assert np.allclose(misses["weight"], 10.0)                              # 1 ÷ 0.1
    assert len(misses) == pytest.approx(19_900 * 0.1, rel=0.1)              # およそ1割が残る
    assert misses["weight"].sum() == pytest.approx(19_900, rel=0.1)         # 重みを掛けると、間引く前の外れの数に戻る
    assert sampled["combo"].is_monotonic_increasing                         # 行の並びは元のまま


def test_間引きは同じ年なら毎回同じ行_年が違えば違う行() -> None:
    table = _many_rows(5_000, hit_count=10)
    sampling = MissSampling({QUINELLA: 0.2})
    first, again = sampling.sample(QUINELLA, table, 2024), sampling.sample(QUINELLA, table, 2024)
    other_year = sampling.sample(QUINELLA, table, 2025)
    assert list(first["combo"]) == list(again["combo"])
    assert list(first["combo"]) != list(other_year["combo"])


def test_学習データは_市場の確率のロジットを出発点に_重みを行ごとに持つ() -> None:
    payouts = pd.DataFrame({"race_id": [race.RACE], "combo": ["0102"], "yen": [700]})
    rows = MissSampling({QUINELLA: 1.0}).sample(QUINELLA, _labeled(QUINELLA, payouts), 2025)
    data = ModelDataFactory(QUINELLA).training(rows)
    assert list(data.features.columns) == list(CATALOGS[QUINELLA].names) and data.label_name == "hit"
    assert data.label.sum() == 1 and data.categorical_columns == ()
    assert data.baseline.known_from is PredictionTiming.RACE_DAY
    q = race.market_probability(QUINELLA, (1, 2))
    assert data.baseline.probabilities().iloc[0] == pytest.approx(q, abs=1e-6)
    assert data.weight is not None and len(data.weight) == len(data) == 6


def test_予測用データは_払戻が無くても作れる() -> None:
    table = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), race.boards())[QUINELLA]
    data = ModelDataFactory(QUINELLA).prediction(table)
    assert len(data) == 6 and data.timing is PredictionTiming.RACE_DAY and data.baseline is not None
