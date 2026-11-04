"""1着・2着・3着を分けて市場に合わせる部品（条件つきロジット・票の表・券種ごとの確率・買い方・成績）を、架空の値で確かめる。"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pandas as pd
import pytest

from 地方の万馬券.analysis.positions.conditional_logit import ConditionalLogit
from 地方の万馬券.analysis.positions.pool_tables_builder import PoolTablesBuilder
from 地方の万馬券.analysis.positions.position_model import EV, PROBABILITY, PositionModel
from 地方の万馬券.analysis.positions.ticket_plan import TicketPlan
from 地方の万馬券.analysis.positions.ticket_probabilities import TicketProbabilities
from 地方の万馬券.analysis.positions.ticket_summary import TicketSummary

_BASE_RACE = 2024010101010100


def test_条件つきロジットは_作った係数を取り戻す():
    rng = np.random.default_rng(1)
    groups, X, y = [], [], []
    true = np.array([1.0, -0.5])
    for g in range(3000):
        x = rng.normal(size=(5, 2))
        p = np.exp(x @ true)
        p /= p.sum()
        chosen = rng.choice(5, p=p)
        groups.extend([g] * 5)
        X.append(x)
        y.extend([1.0 if i == chosen else 0.0 for i in range(5)])
    beta = ConditionalLogit().fit(np.vstack(X), np.array(groups), np.array(y))
    assert beta == pytest.approx(true, abs=0.15)
    p = ConditionalLogit().probabilities(np.vstack(X) @ beta, np.array(groups))
    assert pd.Series(p).groupby(np.array(groups)).sum().to_numpy() == pytest.approx(np.ones(3000))


def _season(n_races: int = 40, n_horses: int = 6, seed: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """架空の1期間: 出走の行（確率つき）と、3連単・馬単・3連複・複勝の確定オッズ。3連単の払戻は 1着→3着の組に付ける。"""
    rng = np.random.default_rng(seed)
    horses, trifecta, exacta, trio, place = [], [], [], [], []
    for r in range(n_races):
        race_id = _BASE_RACE + r
        strength = rng.dirichlet(np.ones(n_horses) * 2)
        order = rng.permutation(n_horses)           # 着順（0 が1着）
        finish = np.empty(n_horses, dtype=int)
        finish[order] = np.arange(1, n_horses + 1)
        for i in range(n_horses):
            p1 = strength[i]
            horses.append({"race_id": race_id, "race_date": f"2024-01-{(r % 28) + 1:02d}", "horse_no": i + 1, "popularity": int(np.argsort(-strength).tolist().index(i)) + 1,
                           "win_odds": round(0.8 / p1, 1), "finish": finish[i], "p1": p1, "p1_lgb": p1 * 0.9, "p1_cat": p1 * 1.1,
                           "p3": min(3 * p1, 0.95), "p3_lgb": min(3 * p1, 0.95) * 0.95, "p3_cat": min(3 * p1, 0.95) * 1.05})
            place.append({"race_id": race_id, "a": i + 1, "odds_lo": round(0.8 / min(3 * p1, 0.95), 1), "odds_hi": round(1.0 / min(3 * p1, 0.95), 1)})
        for a, b, c in permutations(range(n_horses), 3):
            prob = strength[a] * strength[b] / (1 - strength[a]) * strength[c] / (1 - strength[a] - strength[b])
            won = (finish[a], finish[b], finish[c]) == (1, 2, 3)
            trifecta.append({"race_id": race_id, "first": a + 1, "second": b + 1, "third": c + 1, "odds": round(0.725 / prob, 1), "payout": int(72.5 / prob) if won else 0})
        for a, b in permutations(range(n_horses), 2):
            exacta.append({"race_id": race_id, "a": a + 1, "b": b + 1, "odds": round(0.75 / (strength[a] * strength[b] / (1 - strength[a])), 1)})
        for a, b, c in permutations(range(n_horses), 3):
            if a < b < c:
                trio.append({"race_id": race_id, "a": a + 1, "b": b + 1, "c": c + 1, "odds": round(0.725 / (6 * strength[a] * strength[b] * strength[c]), 1)})
    return pd.DataFrame(horses), pd.DataFrame(trifecta), pd.DataFrame(exacta), pd.DataFrame(trio), pd.DataFrame(place)


def test_票の表を作って_1着2着3着を当てはめると_組の確率はレースごとに1になる():
    tables = PoolTablesBuilder().build(*_season())
    assert len(tables.horses) == 40 * 6
    assert len(tables.combos) == 40 * 6 * 5 * 4
    assert len(tables.pairs) == 40 * 6 * 5
    assert tables.combos.groupby("race_id")["m"].sum().to_numpy() == pytest.approx(np.ones(40))
    model = PositionModel()
    coefficients = model.fit([tables])
    assert set(coefficients.first) == set(model.first_features)
    combos = model.predict(tables, coefficients)
    assert combos.groupby("race_id")[PROBABILITY].sum().to_numpy() == pytest.approx(np.ones(40))
    assert (combos[EV] > 0).all()
    assert combos["payout"].gt(0).sum() == 40
    rows = coefficients.rows("試し")
    assert len(rows) == len(model.first_features) + len(model.second_features) + len(model.third_features)


def test_券種ごとの確率は_3連単の組の確率の足し合わせ():
    race = _BASE_RACE
    combos = pd.DataFrame([{"race_id": race, "first": a, "second": b, "third": c} for a, b, c in permutations([1, 2, 3, 4], 3)])
    combos[PROBABILITY] = 1.0 / len(combos)
    frames = pd.DataFrame({"race_id": [race] * 4, "horse_no": [1, 2, 3, 4], "frame_no": [1, 1, 2, 3]})
    tables = TicketProbabilities().of(combos, frames)
    assert tables["単勝"][PROBABILITY].sum() == pytest.approx(1.0)
    assert tables["複勝"][PROBABILITY].sum() == pytest.approx(3.0)
    assert tables["馬単"][PROBABILITY].sum() == pytest.approx(1.0)
    assert len(tables["馬連"]) == 6 and tables["馬連"][PROBABILITY].sum() == pytest.approx(1.0)
    assert len(tables["3連複"]) == 4 and tables["3連複"][PROBABILITY].sum() == pytest.approx(1.0)
    assert tables["ワイド"][PROBABILITY].sum() == pytest.approx(3.0)
    bracket = tables["枠連"].set_index(["a", "b"])[PROBABILITY]
    assert bracket[(1, 1)] == pytest.approx(tables["馬連"].set_index(["a", "b"])[PROBABILITY][(1, 2)])
    assert bracket.sum() == pytest.approx(1.0)


def test_買い方は_期待値の線とオッズの範囲で選び_名前が読める():
    table = pd.DataFrame({"race_id": [_BASE_RACE] * 4, "a": [1, 2, 3, 4], PROBABILITY: [0.5, 0.2, 0.1, 0.01], "odds": [1.8, 6.0, 20.0, 150.0], "payout": [180, 0, 0, 0]})
    chosen = TicketPlan("単勝", 1.0, 0.0, 30.0).choose(table)
    assert set(chosen["a"]) == {2, 3}
    assert TicketPlan("3連単", 1.05, 10.0, 200.0).label == "10〜200倍・期待値 1.05 以上"
    assert TicketPlan("枠連").label == "全部・期待値 1 以上"
    wide = pd.DataFrame({"race_id": [_BASE_RACE], "a": [1], "b": [2], PROBABILITY: [0.5], "odds_lo": [2.0], "odds_hi": [3.0], "payout": [250]})
    assert len(TicketPlan("ワイド", 1.2).choose(wide)) == 1


def test_成績の行は_回収率と的中と落ち込みを数える():
    races = pd.DataFrame({"race_id": [_BASE_RACE, _BASE_RACE + 1], "race_date": ["2024-01-01", "2024-01-02"]})
    chosen = pd.DataFrame({"race_id": [_BASE_RACE, _BASE_RACE, _BASE_RACE + 1], PROBABILITY: [0.2, 0.1, 0.3], "payout": [500, 0, 0]})
    row = TicketSummary().row("単勝", "全部・期待値 1 以上", "2024年", chosen, races)
    assert row["点数"] == 3 and row["投資"] == "300円" and row["払戻"] == "500円" and row["回収率"] == "166.7%"
    assert row["的中"] == 1 and row["的中率"] == "50.0%" and row["最大の落ち込み"] == "-100円"
    monthly = TicketSummary().monthly(chosen, races)
    assert list(monthly["月"]) == ["2024-01"] and monthly["損益"].iloc[0] == 200
