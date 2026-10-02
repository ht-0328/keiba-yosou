"""複勝以外の券種を確かめる部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 回収率100超.analysis.backtest import StakedPayback
from 回収率100超.analysis.market import SternProbabilities
from 回収率100超.analysis.tickets import (
    KINDS_BY_KEY,
    ComboProbability,
    LineStudy,
    MarkTickets,
    OddsBandCalibrator,
    RaceMarks,
    RaceWinTable,
    WinBasedSource,
    YearTicketScorer,
)

HARVILLE = ComboProbability(SternProbabilities(1.0, 1.0))


def _wins(*values: float) -> np.ndarray:
    """馬番の順の勝率 18個（残りは 0）。"""
    return np.r_[values, np.zeros(18 - len(values))]


def test_買い目の番号は馬番を18進で並べた値() -> None:
    assert KINDS_BY_KEY["trifecta"].flat_index(np.array([[3, 1, 5]]))[0] == 652
    assert KINDS_BY_KEY["quinella"].flat_index(np.array([[1, 2]]))[0] == 1


def test_3連単の確率は全部の買い目で合計1() -> None:
    table = HARVILLE.table(KINDS_BY_KEY["trifecta"], _wins(0.4, 0.3, 0.2, 0.1))
    assert table.sum() == pytest.approx(1.0)


def test_3連複の確率は並びの違う3連単の合計() -> None:
    wins = _wins(0.4, 0.3, 0.2, 0.1)
    trio = HARVILLE.table(KINDS_BY_KEY["trio"], wins)
    trifecta = HARVILLE.table(KINDS_BY_KEY["trifecta"], wins)
    orders = np.array([[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]])
    index = KINDS_BY_KEY["trio"].flat_index(np.array([[1, 2, 3]]))[0]
    assert trio[index] == pytest.approx(trifecta[KINDS_BY_KEY["trifecta"].flat_index(orders)].sum())


def test_出走しない馬番を含む買い目は確率0() -> None:
    table = HARVILLE.table(KINDS_BY_KEY["quinella"], _wins(0.5, 0.3, 0.2))
    assert table[KINDS_BY_KEY["quinella"].flat_index(np.array([[1, 5]]))[0]] == 0.0


def test_較正の倍率は実績が無ければ1() -> None:
    calibrator = OddsBandCalibrator((0, 10, 1e9))
    assert calibrator.factors(np.array([5.0, 50.0])) == pytest.approx([1.0, 1.0])


def test_較正の倍率は当たりが見込みより少ない帯で1より小さい() -> None:
    calibrator = OddsBandCalibrator((0, 10, 1e9), shrink=20.0)
    calibrator.add(np.array([50.0] * 100), np.full(100, 0.5), np.r_[np.ones(10), np.zeros(90)])
    assert calibrator.factors(np.array([50.0]))[0] == pytest.approx((10 + 20) / (50 + 20))
    assert calibrator.factors(np.array([5.0]))[0] == pytest.approx(1.0)


def test_勝率の表はレースで合計1にそろえ_居ない馬番は0() -> None:
    table = RaceWinTable(pd.Series([7, 7, 7]), pd.Series([1, 2, 4]), pd.Series([0.2, 0.2, 0.4]))
    wins = table.get(7)
    assert wins.sum() == pytest.approx(1.0)
    assert wins[2] == 0.0
    assert wins[3] == pytest.approx(0.5)
    assert table.get(8) is None


def test_期待値は直した確率と見込みの額の積で_当たりに払戻が付く() -> None:
    kind = KINDS_BY_KEY["win"]
    wins = RaceWinTable(pd.Series([1, 1]), pd.Series([1, 2]), pd.Series([0.6, 0.4]))
    odds = pd.DataFrame({"rid": [1, 1], "h1": [1, 2], "odds": [1.5, 3.0]})
    payouts = pd.DataFrame({"rid": [1], "h1": [2], "payout": [300]})
    score = YearTicketScorer(kind, WinBasedSource(HARVILLE, wins)).score(
        odds, payouts, OddsBandCalibrator(kind.bands), odds["odds"])
    rows = score.all_rows.set_index("flat")
    assert rows.loc[1, "ev"] == pytest.approx(0.4 * 3.0)
    assert rows.loc[1, "payout"] == 300
    assert rows.loc[0, "payout"] == 0
    assert list(score.candidates["flat"]) == [1]


def _race() -> pd.DataFrame:
    """16頭立ての架空のレース。3着以内の確率は馬番の順に高い。9番は穴馬で複勝の期待値が高い。"""
    horses = np.arange(1, 17)
    return pd.DataFrame({
        "rid": 1, "horse_no": horses, "p_placed": np.linspace(0.6, 0.05, 16),
        "market_placed": np.linspace(0.6, 0.05, 16), "popularity": horses, "field": 16,
        "place_ev": np.where(horses == 9, 1.3, 0.8),
    }).assign(market_placed=lambda t: np.where(t["horse_no"] == 12, 0.01, t["market_placed"]))


def test_印は3着以内の確率の順に付け_星は期待値の高い穴馬() -> None:
    marks = RaceMarks().build(_race()).iloc[0]
    assert [marks["◎"], marks["○"], marks["▲"], marks["△1"], marks["△2"]] == [1, 2, 3, 4, 5]
    assert marks["☆"] == 9
    assert marks["注"] == 12


def test_印のルールの3連複は並びだけ違う組を1点にまとめる() -> None:
    marks = pd.DataFrame([{"rid": 1, "◎": 1, "○": 2, "▲": 3, "△1": 4, "△2": 5, "☆": np.nan, "注": 6}])
    tickets = MarkTickets().build(marks)
    trio = tickets[(tickets["kind"] == "trio") & (tickets["variant"] == "通常")]
    # ◎ 軸 − {○,▲} − {○,▲,△,△}: {1,2,3}・{1,2,4}・{1,2,5}・{1,3,4}・{1,3,5} の5点。
    assert len(trio) == 5
    assert trio["flat"].is_unique
    assert tickets[tickets["variant"] == "荒れそう"].empty


def test_賭け金の違う買い目の回収率は金額で数える() -> None:
    summary = StakedPayback(rounds=100).summarize(
        pd.Series(["d1", "d1", "d2"]), pd.Series([100.0, 30.0, 30.0]), pd.Series([0.0, 1000.0, 0.0]))
    assert summary.rate == pytest.approx(300 / 160 * 100)
    assert summary.hits == 1


def test_点数の上限は期待値の高い順に残す() -> None:
    tickets = pd.DataFrame({"rid": [1, 1, 1], "ev": [1.1, 1.6, 1.3]})
    bought = LineStudy().select(tickets, 1.0, cap=2)
    assert sorted(bought["ev"]) == [1.3, 1.6]


def test_線は前半の年だけで選ぶ() -> None:
    # 前半は線 1.0（2点とも買う）が 150%、線 1.5（1点だけ）が 0%。後半は線 1.0 が 50% に落ちる。
    # 後半を見れば線 1.5 が良いが、選ぶのは前半で良い線 1.0 で、後半で 100% に届かないので不採用。
    rows = []
    for year in (2019, 2020, 2021, 2022):
        for i in range(40):
            rows.append({"rid": year * 100 + i, "year": year, "day": f"{year}-{i}", "stake": 100.0,
                         "ev": 1.05, "payout": 300.0 if year < 2022 else 0.0})
            rows.append({"rid": year * 100 + i, "year": year, "day": f"{year}-{i}", "stake": 100.0,
                         "ev": 1.55, "payout": 0.0 if year < 2022 else 100.0})
    study = LineStudy(StakedPayback(rounds=50)).run(pd.DataFrame(rows), cap=None)
    assert study.chosen.line == 1.0
    assert not study.adopted
