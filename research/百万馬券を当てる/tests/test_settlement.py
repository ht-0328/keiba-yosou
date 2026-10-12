"""研究の精算と成績のまとめのテスト。架空の値だけを使い、DB と保存した予測は使わない。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.dataset import RACE_DATE, RACE_ID

from 百万馬券を当てる.analysis.betting_summary import BettingSummary
from 百万馬券を当てる.analysis.day_bootstrap import DayBootstrap
from 百万馬券を当てる.analysis.ticket_maker import COMBO, ODDS, PLAN, STAKE
from 百万馬券を当てる.analysis.ticket_settler import HIT, PAYOUT, TicketSettler
from 百万馬券を当てる.analysis.winning_combos import trifecta_winners, trio_winners


def test_同着でも当たりの組を全部作る() -> None:
    assert trifecta_winners({1: 1, 2: 2, 3: 3, 4: 4}) == {(1, 2, 3)}
    assert trifecta_winners({1: 1, 2: 1, 3: 3}) == {(1, 2, 3), (2, 1, 3)}
    assert trifecta_winners({1: 1, 2: 2, 3: 3, 4: 3}) == {(1, 2, 3), (1, 2, 4)}
    assert trio_winners({5: 1, 2: 2, 9: 3}) == {(2, 5, 9)}


def test_精算は当たりの組だけに確定オッズと掛け金の積を払う() -> None:
    tickets = pd.DataFrame({PLAN: "甲", RACE_ID: ["r1", "r1"], RACE_DATE: pd.to_datetime(["2021-01-05"] * 2),
                            COMBO: [(1, 2, 3), (3, 2, 1)], STAKE: [500, 100], ODDS: [2_500.0, 900.0]})
    settled = TicketSettler().settle(tickets, {"r1": {(1, 2, 3)}})
    assert settled[HIT].tolist() == [True, False]
    assert settled[PAYOUT].tolist() == [1_250_000.0, 0.0]


def test_成績は帯の回数と大きい当たりを除いた回収率と落ち込みと連敗を出す() -> None:
    days = pd.to_datetime(["2021-01-05", "2021-01-06", "2021-01-07", "2021-01-08"])
    settled = pd.DataFrame({RACE_ID: ["a", "b", "c", "d"], RACE_DATE: days, STAKE: [10_000] * 4,
                            HIT: [False, False, True, True], PAYOUT: [0.0, 0.0, 1_500_000.0, 20_000.0]})
    row = BettingSummary(DayBootstrap(draws=50)).row(settled, years=1)
    assert row["帯の回数"] == 1 and row["最大の連敗"] == 2
    assert row["回収率"] == pytest.approx(1_520_000 / 40_000)
    assert row["いちばん大きい当たりを除いた回収率"] == pytest.approx(20_000 / 40_000)
    assert row["いちばん深い落ち込み"] == 20_000  # 始めの2レースで 2万円負けた

