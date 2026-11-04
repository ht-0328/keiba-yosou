"""3連単の組の確率・買い目の組み方・成績の数え方を、架空の値で確かめる。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from 地方の万馬券.analysis.payout_band import BIG, SOLID
from 地方の万馬券.analysis.popularity_band import FAVORITE, LONGSHOT, MIDDLE
from 地方の万馬券.analysis.trifecta.harville_combos import HarvilleCombos
from 地方の万馬券.analysis.trifecta.race_market import EDGE, MARKET_UPSET
from 地方の万馬券.analysis.trifecta.simulator import TrifectaSimulator
from 地方の万馬券.analysis.trifecta.strategy import Strategy
from 地方の万馬券.analysis.trifecta.ticket_plan import TicketPlan


def test_組の確率は全部で1になり_式のとおり():
    horses = pd.DataFrame({"horse_no": [1, 2, 3], "strength": [0.5, 0.3, 0.2]})
    combos = HarvilleCombos().combos(horses)
    assert len(combos) == 6
    assert combos["probability"].sum() == pytest.approx(1.0)
    row = combos[(combos["first"] == 1) & (combos["second"] == 2) & (combos["third"] == 3)].iloc[0]
    assert row["probability"] == pytest.approx(0.5 * 0.3 / 0.5 * 0.2 / 0.2)


def _runners() -> pd.DataFrame:
    """1レース 8頭。人気馬 3頭（3番人気の差がいちばん低い）、中穴 3頭、大穴 2頭。大荒れのレース。"""
    return pd.DataFrame({
        "race_id": ["r1"] * 8, "horse_no": range(1, 9), "popularity": range(1, 9),
        "band": [FAVORITE] * 3 + [MIDDLE] * 3 + [LONGSHOT] * 2,
        EDGE: [0.05, 0.02, -0.10, 0.03, 0.01, -0.02, 0.04, -0.01], MARKET_UPSET: [BIG] * 8,
    })


def _combos_and_odds() -> tuple[pd.DataFrame, pd.DataFrame]:
    combos = HarvilleCombos().all_races(pd.DataFrame({"race_id": ["r1"] * 8, "horse_no": range(1, 9), "strength": [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05]}))
    odds = combos[["race_id", "first", "second", "third"]].copy()
    odds["odds"] = 2.0 / combos["probability"]      # どの組も期待値 2.0
    return combos, odds


def test_消した人気馬を含む組と_荒れ具合に無い型は買わない():
    combos, odds = _combos_and_odds()
    strategy = Strategy("t", {BIG: ("人中大",)}, max_points=1000)
    tickets = TicketPlan(strategy).build(_runners(), combos, odds)
    assert set(tickets["pattern"]) == {"人中大"}
    assert 3 not in set(tickets["first"])                  # 3番人気（差がいちばん低い）は消
    assert set(tickets["first"]) == {1, 2}
    assert set(tickets["third"]) == {7, 8}
    assert len(tickets) == 2 * 3 * 2


def test_固いレースは型が無ければ買わない_期待値と点数の上限も効く():
    combos, odds = _combos_and_odds()
    runners = _runners().assign(**{MARKET_UPSET: SOLID})
    assert TicketPlan(Strategy("t", {BIG: ("人中大",)})).build(runners, combos, odds).empty
    few = TicketPlan(Strategy("t", {SOLID: ("全",)}, max_points=5, eliminate=False)).build(runners, combos, odds)
    assert len(few) == 5
    none = TicketPlan(Strategy("t", {SOLID: ("全",)}, ev_min=3.0)).build(runners, combos, odds)
    assert none.empty


def test_成績は払戻を当てて数える():  # noqa: E302
    tickets = pd.DataFrame({"race_id": ["r1", "r1", "r2"], "first": [1, 2, 1], "second": [2, 1, 2], "third": [3, 3, 3]})
    results = pd.DataFrame({"race_id": ["r1"], "first": [1], "second": [2], "third": [3], "payout": [12_000]})
    races = pd.DataFrame({"race_id": ["r1", "r2"], "race_date": [date(2026, 1, 1), date(2026, 1, 2)], "period": ["t", "t"]})
    simulator = TrifectaSimulator(results)
    rows = simulator.summarize("x", simulator.settle(tickets, races), races)
    row = rows[0]
    assert row["点数"] == 3 and row["投資"] == "300円" and row["払戻"] == "12,000円"
    assert row["的中レース"] == 1 and row["万馬券の的中"] == 1 and row["10万馬券の的中"] == 0
    assert row["最長の連敗（日）"] == 1


def test_年ごとの成績は年で分けて数える():
    tickets = pd.DataFrame({"race_id": ["r1", "r2"], "first": [1, 1], "second": [2, 2], "third": [3, 3]})
    results = pd.DataFrame({"race_id": ["r1"], "first": [1], "second": [2], "third": [3], "payout": [500]})
    races = pd.DataFrame({"race_id": ["r1", "r2"], "race_date": [date(2024, 12, 31), date(2025, 1, 1)], "period": ["t", "t"]})
    simulator = TrifectaSimulator(results)
    rows = simulator.summarize_by_year("x", simulator.settle(tickets, races), races)
    assert [row["期間"] for row in rows] == ["2024年", "2025年"]
    assert rows[0]["払戻"] == "500円" and rows[1]["払戻"] == "0円"


def test_レース単位の線に届かないレースは丸ごと買わない():
    combos, odds = _combos_and_odds()
    runners = _runners()
    base = TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=5)).build(runners, combos, odds)
    hit = float(base["probability"].sum())                    # 5点の当たる見込み
    assert 0 < hit < 1
    assert TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=5, race_hit_min=hit + 0.01)).build(runners, combos, odds).empty
    assert len(TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=5, race_hit_min=hit - 1e-9)).build(runners, combos, odds)) == 5
    assert TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=5, race_ev_min=2.5)).build(runners, combos, odds).empty   # どの組も期待値 2.0


def test_3着以内に合わせた勝つ力はHarvilleの3着以内率が3着以内の確率に合う():
    from yosou.shared.feature.odds import HarvillePlaces
    from yosou.shared.feature.odds.column_names import TOP3_RATE
    from 地方の万馬券.analysis.trifecta.fitted_strength import Top3FittedStrength

    race_ids = pd.Series(["r1"] * 6 + ["r2"] * 5)
    truth = pd.Series([0.4, 0.25, 0.15, 0.1, 0.06, 0.04, 0.5, 0.2, 0.15, 0.1, 0.05])
    target = HarvillePlaces().places(race_ids, truth)[TOP3_RATE]
    start = pd.Series([1.0 / 6] * 6 + [1.0 / 5] * 5)                        # 何も知らない状態から始める
    fitted = Top3FittedStrength().fit(race_ids, start, target)
    got = HarvillePlaces().places(race_ids, fitted)[TOP3_RATE]
    assert (got - target).abs().max() < 1e-3
    assert abs(fitted[:6].sum() - 1.0) < 1e-9 and abs(fitted[6:].sum() - 1.0) < 1e-9


def test_1着だけ別の勝つ力を使える():
    horses = pd.DataFrame({"horse_no": [1, 2, 3, 4], "strength": [0.4, 0.3, 0.2, 0.1], "first_strength": [0.1, 0.2, 0.3, 0.4]})
    combos = HarvilleCombos().combos(horses)
    first = combos.groupby("first")["probability"].sum()
    assert abs(first[4] - 0.4) < 1e-9 and abs(first[1] - 0.1) < 1e-9       # 1着の確率は first_strength
    assert abs(combos["probability"].sum() - 1.0) < 1e-9


def test_縮めは組の確率を市場の組の確率に寄せる():
    combos, _ = _combos_and_odds()
    odds = combos[["race_id", "first", "second", "third"]].assign(odds=float(len(combos)))   # 市場はどの組も同じ確率
    runners = _runners()
    plain = TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=1000, eliminate=False, ev_min=0.0)).build(runners, combos, odds)
    same = TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=1000, eliminate=False, ev_min=0.0, shrink=1.0)).build(runners, combos, odds)
    flat = TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=1000, eliminate=False, ev_min=0.0, shrink=0.0)).build(runners, combos, odds)
    assert (plain["probability"].to_numpy() == same["probability"].to_numpy()).all()
    assert (flat["probability"] - 1.0 / len(combos)).abs().max() < 1e-9           # 市場と同じ（どの組も同じ確率）
    assert (flat["ev"] - 1.0).abs().max() < 1e-9
    half = TicketPlan(Strategy("t", {BIG: ("全",)}, max_points=1000, eliminate=False, ev_min=0.0, shrink=0.5)).build(runners, combos, odds)
    assert half["probability"].max() < plain["probability"].max()                 # 高い組は下がる


def test_買い方は名前の先頭の記号で絞れる():
    from 地方の万馬券.analysis.trifecta.trifecta_study import TrifectaStudySettings

    settings = TrifectaStudySettings(date(2024, 1, 1), date(2026, 1, 1), Path("x"), None,
                                     strategies=(Strategy("L x", {}), Strategy("L1 y", {}), Strategy("T2 z", {})))
    assert [s.name for s in settings.only(("L", "T2")).strategies] == ["L x", "T2 z"]
    assert len(settings.only(()).strategies) == 3
    assert [s.name for s in settings.only(("T*",)).strategies] == [s.name for s in settings.strategies if s.name.startswith("T")]


def test_市場の組の確率はレース内で合計1():
    from 地方の万馬券.analysis.trifecta.combo_market import MARKET, ComboMarket

    odds = pd.DataFrame({"race_id": [1, 1, 1, 2, 2], "first": [1, 1, 2, 1, 2], "second": [2, 3, 1, 2, 1], "third": [3, 2, 3, 3, 3],
                         "odds": [2.0, 4.0, 4.0, 10.0, 10.0]})
    table = ComboMarket().attach(odds)
    assert table.groupby("race_id")[MARKET].sum().round(9).eq(1.0).all()
    assert abs(table.loc[0, MARKET] - 0.5) < 1e-9                               # 1/2 ÷ (1/2 + 1/4 + 1/4)


def test_組の確率の直しは係数を取り戻す():
    import numpy as np
    from 地方の万馬券.analysis.trifecta.combo_calibration import ComboCalibration

    rng = np.random.default_rng(3)
    n = 40_000
    p = pd.Series(np.exp(rng.uniform(np.log(0.0005), np.log(0.05), n)))
    m = pd.Series(np.exp(np.log(p) + rng.normal(0, 0.5, n)))
    truth = np.array([0.3, 0.4, 0.7])                                               # 切片・log p・log m
    z = truth[0] + truth[1] * np.log(p) + truth[2] * np.log(m)
    hit = pd.Series((rng.uniform(size=n) < 1 / (1 + np.exp(-z))).astype(float))
    beta = ComboCalibration().fit(p, m, hit)
    assert np.abs(beta[1:] - truth[1:]).max() < 0.15 and abs(beta[0] - truth[0]) < 0.5   # 傾きは正確、切片は的中が少ないぶん幅がある
    q = ComboCalibration().apply(beta, p, m)
    assert ((q > 0) & (q < 1)).all() and abs(q.sum() - hit.sum()) / hit.sum() < 0.05   # 直した確率の合計は的中の数に合う


def test_直した期待値の買い目は線と上限で選ぶ():
    from unittest.mock import Mock

    from 地方の万馬券.analysis.trifecta.calibration_study import CalibrationStudy, CalibrationStudySettings

    table = pd.DataFrame({"race_id": [1, 1, 1, 2], "first": [1, 2, 3, 1], "second": [2, 3, 1, 2], "third": [3, 1, 2, 3],
                          "probability": [0.1, 0.1, 0.1, 0.1], "odds": [10.0, 20.0, 30.0, 5.0], "calibrated": [0.2, 0.06, 0.03, 0.1]})
    table["ev"] = table["calibrated"] * table["odds"]                               # 2.0, 1.2, 0.9, 0.5
    study = CalibrationStudy(Mock(), CalibrationStudySettings(date(2024, 1, 1), Path("x"), 2024, max_points=1))
    chosen = study._choose(table, 1.0)
    assert list(chosen["race_id"]) == [1] and list(chosen["first"]) == [1]           # レース1 は上限 1点、レース2 は線に届かない
    assert chosen.loc[0, "probability"] == 0.2                                        # 確率は直した確率


def test_3連複の組の確率は並びの和で_組は馬番の小さい順():
    horses = pd.DataFrame({"horse_no": [3, 1, 2], "strength": [0.5, 0.3, 0.2]})
    trios = HarvilleCombos().trios(horses)
    assert len(trios) == 1
    assert tuple(trios.iloc[0][["first", "second", "third"]]) == (1, 2, 3)
    assert trios.iloc[0]["probability"] == pytest.approx(1.0)


def test_3連複の型は人中大の順に並べる():
    from 地方の万馬券.analysis.trifecta.strategy import TRIO
    combos = HarvilleCombos().all_races(pd.DataFrame({"race_id": ["r1"] * 8, "horse_no": range(1, 9), "strength": [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05]}), trio=True)
    odds = combos[["race_id", "first", "second", "third"]].assign(odds=2.0 / combos["probability"])
    tickets = TicketPlan(Strategy("t", {BIG: ("人中大",)}, ticket=TRIO, max_points=1000)).build(_runners(), combos, odds)
    assert set(tickets["pattern"]) == {"人中大"}
    assert len(tickets) == 2 * 3 * 2
