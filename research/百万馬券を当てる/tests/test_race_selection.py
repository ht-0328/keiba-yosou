"""第1段（レース選び）の部品のテスト。架空の値だけを使い、DB と保存した表は使わない。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.dataset import RACE_DATE, RACE_ID

from 百万馬券を当てる.analysis.crowded_split_rule import crowded_split_score
from 百万馬券を当てる.analysis.day_bootstrap import DayBootstrap
from 百万馬券を当てる.analysis.day_race_picker import DayRacePicker
from 百万馬券を当てる.analysis.lift_table import LIFT, LiftTable
from 百万馬券を当てる.analysis.obi_rules import BIG, OBI, OTHER, payout_class
from 百万馬券を当てる.analysis.race_frame import PAYOUT_CLASS
from 百万馬券を当てる.analysis.selection_summary import SelectionSummary


def test_払戻の段は100万円以上が帯で10万円以上が大荒れ() -> None:
    assert payout_class(1_000_000) == OBI
    assert payout_class(999_990) == BIG
    assert payout_class(100_000) == BIG
    assert payout_class(99_990) == OTHER


def test_集まり方はその値の割合を全体の割合で割った値() -> None:
    frame = pd.DataFrame({"頭数": ["多い"] * 40 + ["少ない"] * 60, "帯": [1] * 8 + [0] * 32 + [1] * 2 + [0] * 58})
    table = LiftTable("帯", min_count=10).table(frame, "頭数")
    # 全体の割合 0.10、多い 0.20、少ない 0.0333…
    assert table.loc["多い", LIFT] == pytest.approx(2.0)
    assert table.loc["少ない", LIFT] == pytest.approx(1 / 3)


def test_開催日ごとに点数のいちばん高いレースを1つ選ぶ() -> None:
    races = pd.DataFrame({
        RACE_ID: ["a1", "a2", "b1", "b2"],
        RACE_DATE: pd.to_datetime(["2021-01-05", "2021-01-05", "2021-01-06", "2021-01-06"]),
        "点数": [0.1, 0.3, 0.2, 0.2],
    })
    picked = DayRacePicker("点数").pick(races)
    # 同じ点数なら早いレース（b1）
    assert picked[RACE_ID].tolist() == ["a2", "b1"]


def test_多頭数のレースは人気の割れ方に関係なく多頭数でないレースより上() -> None:
    races = pd.DataFrame({"出走頭数": [16, 12], "市場勝率の上位3頭の合計": [0.9, 0.3]})
    scores = crowded_split_score(races)
    assert scores[0] > scores[1]


def test_選んだレースの帯の集まり方と拾い方() -> None:
    days = pd.to_datetime(["2021-01-05"] * 4 + ["2021-01-06"] * 4)
    races = pd.DataFrame({RACE_ID: list("abcdefgh"), RACE_DATE: days,
                          PAYOUT_CLASS: [OBI, OTHER, OTHER, OTHER, OTHER, OBI, OTHER, OTHER]})
    picked = races[races[RACE_ID].isin(["a", "e"])]
    row = SelectionSummary(DayBootstrap(draws=50)).row(picked, races)
    # 選んだ2レースのうち帯は1（0.5）、全体は 2/8（0.25）なので 2倍。全部の帯2つのうち1つを拾った
    assert row["帯の集まり方"] == pytest.approx(2.0)
    assert row["帯の拾い方"] == pytest.approx(0.5)
