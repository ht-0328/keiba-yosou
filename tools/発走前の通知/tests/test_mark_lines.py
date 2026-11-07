"""MarkLines（通知の文の印の行）のテスト。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK

from 発走前の通知.mark_lines import MarkLines


def test_印ごとに1行_同じ印はつなぎ_無印は書かず_馬番が無ければ横線() -> None:
    table = pd.DataFrame([
        {MARK: "◎", HORSE_NO: 9, HORSE_NAME: "馬A"},
        {MARK: "△", HORSE_NO: 13, HORSE_NAME: "馬B"},
        {MARK: "△", HORSE_NO: 4, HORSE_NAME: "馬C"},
        {MARK: "－", HORSE_NO: 1, HORSE_NAME: "馬D"},
        {MARK: "消", HORSE_NO: None, HORSE_NAME: "馬E"},
        {MARK: "○", HORSE_NO: 2, HORSE_NAME: "馬F"},
    ])
    assert MarkLines().lines(table) == ["◎ 9 馬A", "○ 2 馬F", "△ 13 馬B・4 馬C", "消 - 馬E"]
