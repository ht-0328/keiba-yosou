"""決着の型の表と事情の割合の表を、架空の値で確かめる。"""

from __future__ import annotations

import pandas as pd

from 地方の万馬券.analysis.circumstance_share_table import CircumstanceShareTable
from 地方の万馬券.analysis.outcome_pattern_table import PATTERN_COUNTS, PATTERN_ORDERED, OutcomePatternTable
from 地方の万馬券.analysis.payout_band import BIG, SOLID
from 地方の万馬券.analysis.runner_circumstances import CIRCUMSTANCES


def test_決着の型は_1着から3着の順と順不同の2つ():
    placed = pd.DataFrame({
        "race_id": ["r1", "r1", "r1", "r2", "r2"], "finish": [2, 1, 3, 1, 2], "band": ["中", "人", "大", "人", "人"],
    })
    patterns = OutcomePatternTable().patterns(placed).set_index("race_id")
    assert patterns.loc["r1", PATTERN_ORDERED] == "人中大"
    assert patterns.loc["r1", PATTERN_COUNTS] == "人1中1大1"
    assert "r2" not in patterns.index     # 3着がそろわないレースは出さない


def test_配当の帯ごとに型の割合を数える():
    races = pd.DataFrame({
        "payout_band": [BIG, BIG, SOLID], "trifecta_payout": [150_000, 250_000, 3_000],
        PATTERN_COUNTS: ["人1中1大1", "人1中1大1", "人3中0大0"],
    })
    table = OutcomePatternTable().build(races, PATTERN_COUNTS, title="t")
    rows = {(row[0], row[1]): row for row in table.rows}
    assert rows[(BIG, "人1中1大1")][2] == 2
    assert rows[(BIG, "人1中1大1")][3] == "100.0%"
    assert rows[(SOLID, "全部")][2] == 1


def test_事情の割合の表は倍率の大きい順():
    columns = {name: [False] * 4 for name in CIRCUMSTANCES}
    columns["遠征"] = [True, True, False, False]
    columns["連闘"] = [True, False, True, False]
    base = pd.DataFrame(columns)
    event = base.iloc[[0, 1]]        # 事象の2頭はどちらも遠征、連闘は1頭
    table = CircumstanceShareTable().build(event, base, title="t")
    first = table.rows[0]
    assert first[0] == "遠征" and first[5] == 2.0     # 事象 100% ÷ 母集団 50%
    by_name = {row[0]: row for row in table.rows}
    assert by_name["連闘"][5] == 1.0
