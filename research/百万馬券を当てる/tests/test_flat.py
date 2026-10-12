"""docs/06（1,000倍以上のレースを狙う）の部品のテスト。架空の値だけを使い、DB と保存した表は使わない。"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import RACE_DATE, RACE_ID
from yosou.upset_premise.betting import FlatPlan, RaceHorses

from 百万馬券を当てる.analysis.big_combo_odds import BigComboOdds
from 百万馬券を当てる.analysis.flat_hit_summary import FlatHitSummary
from 百万馬券を当てる.analysis.plain_flat_plan import PlainFlatPlan
from 百万馬券を当てる.analysis.race_table_loader import TRIFECTA_YEN
from 百万馬券を当てる.analysis.selection_precision import SCORE, SelectionPrecision
from 百万馬券を当てる.analysis.ticket_maker import COMBO, STAKE, TicketMaker
from 百万馬券を当てる.analysis.ticket_settler import HIT, PAYOUT, TicketSettler


def test_同じレース数を選んだときの精度を点数ごとに並べる() -> None:
    days = pd.to_datetime(["2021-01-05"] * 4 + ["2021-01-06"] * 4)
    races = pd.DataFrame({RACE_ID: [f"r{i}" for i in range(8)], RACE_DATE: days,
                          TRIFECTA_YEN: [200_000, 50_000, 300_000, 10_000, 150_000, 20_000, 30_000, 40_000],
                          "良い点数": [0.9, 0.2, 0.8, 0.1, 0.7, 0.3, 0.2, 0.1], "悪い点数": [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.6, 0.5]})
    table = SelectionPrecision(per_day_counts=(1.0, 2.0)).table(races, ["良い点数", "悪い点数", "無い点数"])
    assert table[SCORE].tolist() == ["良い点数", "悪い点数"]
    good = table.set_index(SCORE).loc["良い点数"]
    assert good["1レース/日（2）"] == 1.0 and good["2レース/日（4）"] == 0.75 and good["AUC"] == 1.0
    assert table.set_index(SCORE).loc["悪い点数"]["1レース/日（2）"] == 0.0


def test_1000倍以上の組の表はレースごとに辞書で引ける() -> None:
    table = pd.DataFrame({RACE_ID: ["a", "a", "b"], "1着": np.array([1, 2, 3], dtype=np.int8), "2着": np.array([2, 1, 4], dtype=np.int8),
                          "3着": np.array([3, 3, 5], dtype=np.int8), "オッズ": np.array([1500.0, 2000.5, 1000.0], dtype=np.float32)})
    odds = BigComboOdds(table)
    assert len(odds) == 2 and set(odds) == {"a", "b"} and "c" not in odds
    assert odds["a"] == {(1, 2, 3): 1500.0, (2, 1, 3): 2000.5}
    assert odds["b"][(3, 4, 5)] == pytest.approx(1000.0)
    assert BigComboOdds(BigComboOdds.empty_table()).table.empty


def _horses() -> RaceHorses:
    numbers = np.arange(1, 7)
    win = np.linspace(2.0, 1.0, 6)
    return RaceHorses("r1", numbers, win / win.sum(), np.linspace(0.6, 0.1, 6), np.linspace(0.2, 0.7, 6))


def test_元のHarvilleの一律は2着3着の重みを使わない() -> None:
    horses = _horses()
    odds = {order: 1_200.0 for order in permutations(range(1, 7), 3)}
    plain = PlainFlatPlan(500).tickets(horses, odds)
    adopted = FlatPlan(500).tickets(horses, odds)
    assert len(plain) == len(adopted) == 20 and all(stake == 500 for _, stake in plain)
    assert plain[0][0] == (1, 2, 3)  # 1着の確率の高い順そのまま
    assert [combo for combo, _ in plain] != [combo for combo, _ in adopted]  # 今の予想の重みで並びが変わる


def test_一律の買い目の当てた割合は1000倍以上で決まったレースのうち() -> None:
    races = pd.DataFrame({RACE_ID: ["a", "b", "c"], TRIFECTA_YEN: [150_000, 50_000, 200_000]})
    settled = pd.DataFrame({RACE_ID: ["a", "a", "b", "c"], COMBO: [(1, 2, 3), (2, 1, 3), (1, 2, 3), (1, 2, 3)],
                            STAKE: [100] * 4, HIT: [True, False, True, False], PAYOUT: [150_000.0, 0.0, 0.0, 0.0]})
    row = FlatHitSummary().row(settled, races)
    assert row == {"買ったレース": 3, "1,000倍以上で決まったレース": 2, "うち当てたレース": 1, "当てた割合": 0.5}


def test_一律の買い目を小さい表のオッズで作って精算できる() -> None:
    table = pd.DataFrame({RACE_ID: ["r1"] * 3, "1着": np.array([1, 2, 1], dtype=np.int8), "2着": np.array([2, 1, 3], dtype=np.int8),
                          "3着": np.array([3, 3, 2], dtype=np.int8), "オッズ": np.array([1500.0, 2000.0, 900.0], dtype=np.float32)})
    races = pd.DataFrame({RACE_ID: ["r1"], RACE_DATE: pd.to_datetime(["2021-01-05"])})
    tickets = TicketMaker(FlatPlan(100), "一律").make(races, {"r1": _horses()}, {True: BigComboOdds(table)})
    assert sorted(tickets[COMBO]) == [(1, 2, 3), (2, 1, 3)]  # 900倍の組は買わない
    settled = TicketSettler().settle(tickets, {"r1": {(2, 1, 3)}})
    assert settled[PAYOUT].sum() == 200_000.0
