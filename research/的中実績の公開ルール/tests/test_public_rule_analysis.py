"""研究「的中実績の公開ルール」の部品（確率の差し替え・◎ の選び方・1頭1行の表・成績の表）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 的中実績の公開ルール.analysis.day_bootstrap import DayBootstrap
from 的中実績の公開ルール.analysis.horse_table import HorseTable
from 的中実績の公開ルール.analysis.rule_report import RuleReport
from 的中実績の公開ルール.analysis.snapshot_probability import SnapshotProbability
from 的中実績の公開ルール.analysis.top_picks import TopPicks


def test_確率の差し替えは_オッズが同じなら変えず_オッズが下がった馬の確率を上げる() -> None:
    frame = pd.DataFrame({"race_id": ["a"] * 3, "p": [0.5, 0.3, 0.2], "odds": [2.0, 4.0, 8.0], "snapshot_odds": [2.0, 4.0, 8.0]})
    assert np.allclose(SnapshotProbability().of(frame), [0.5, 0.3, 0.2])
    moved = SnapshotProbability().of(frame.assign(snapshot_odds=[2.0, 3.0, 8.0]))
    assert moved.iloc[1] > 0.3 and moved.sum() == pytest.approx(1.0)


def test_本命は30倍以下で期待値が最大の馬_買うのは線以上で上限以下() -> None:
    horses = pd.DataFrame({"race_id": ["a", "a", "a", "b", "b"], "p": [0.30, 0.10, 0.05, 0.4, 0.3], "odds": [3.0, 5.0, 40.0, 2.0, 7.0]})
    tops = TopPicks().of(horses)
    # a は 40倍の馬（期待値 2.0）を候補にせず 5倍の馬（0.5）より 3倍の馬（0.9）。b は 7倍の馬（2.1）
    assert list(tops["odds"]) == [3.0, 7.0]
    assert list(TopPicks.bought(tops, 1.0, 6.0)["race_id"]) == []
    assert list(TopPicks.bought(tops, 0.89, 6.0)["race_id"]) == ["a"]


def test_1頭1行の表は払戻を付けてテスト期間だけ_締め切り前は全頭のオッズがあるレースだけ() -> None:
    predictions = pd.DataFrame({"レースID": ["r1", "r1", "r2", "r2", "r0"], "開催日": ["2025-10-04"] * 4 + ["2019-01-05"],
                                "馬番": [1, 2, 1, 2, 1], "確率": [0.6, 0.2, 0.5, 0.5, 1.0], "期間": ["テスト"] * 4 + ["学習"]})
    odds = pd.DataFrame({"race_id": ["r1", "r1", "r2", "r2", "r0"], "combo": ["01", "02", "01", "02", "01"], "odds": [1.5, 3.0, 2.0, 2.0, 1.1]})
    payouts = pd.DataFrame({"race_id": ["r1"], "combo": ["01"], "yen": [150]})
    snapshot = pd.DataFrame({"race_id": ["r1", "r1", "r2"], "horse_no": [1, 2, 1], "odds": [1.6, 2.8, 2.0]})
    table = HorseTable(predictions, odds, payouts, snapshot)
    final = table.final()
    assert set(final["race_id"]) == {"r1", "r2"} and final["year"].eq(2025).all()
    assert list(final.loc[final["race_id"] == "r1", "p"]) == pytest.approx([0.75, 0.25])
    assert list(final["win_pay"]) == [150.0, 0.0, 0.0, 0.0]
    shot = table.snapshot()
    assert set(shot["race_id"]) == {"r1"} and list(shot["odds"]) == [1.6, 2.8]


def _tops(year: int, pays: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"race_id": [f"{year}-{i}" for i in range(len(pays))], "day": [f"{year}-10-0{1 + i % 2}" for i in range(len(pays))],
                         "year": year, "value": 1.1, "odds": 4.0, "win_pay": pays})


def test_成績の表は期間と年に分け_外れ続きと運の下の端を出す() -> None:
    final = pd.concat([_tops(2021, [400, 0, 0, 0]), _tops(2024, [0, 500])])
    report = RuleReport(final, _tops(2025, [300, 0]), 1.0, 6.0)
    periods = {row[0]: row[1:] for row in report.periods().rows}
    assert periods["確定オッズ・探す期間"][1:6] == [4, "2.0", 1, "25.0%", "100.0%"]
    assert periods["確定オッズ・探す期間"][7] == 3
    assert periods["確定オッズ・確かめる期間"][5] == "250.0%"
    assert periods["10分前のオッズ"][5] == "150.0%"
    assert [row[0] for row in report.years().rows] == [2021, 2024]
    assert len(report.lines().rows) == 36


def test_運の下の端は回収率の幅の中にある() -> None:
    bought = _tops(2021, [400, 0, 0, 0, 300, 0])
    low = DayBootstrap().low(bought)
    assert 0 <= low <= bought["win_pay"].sum() / len(bought)
