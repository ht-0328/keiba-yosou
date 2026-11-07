"""MarkLines（通知の文の印の行）のテスト。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, MARK_REASON

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


def test_本命_星_注_消には印の理由を添え_相手の印には添えない() -> None:
    table = pd.DataFrame([
        {MARK: "◎", HORSE_NO: 9, HORSE_NAME: "馬A", MARK_REASON: "単勝の期待値が1位"},
        {MARK: "○", HORSE_NO: 2, HORSE_NAME: "馬B", MARK_REASON: "3着以内に入る確率が1位"},
        {MARK: "☆", HORSE_NO: 5, HORSE_NAME: "馬C", MARK_REASON: "穴馬の中で複勝の期待値が1位"},
        {MARK: "注", HORSE_NO: 6, HORSE_NAME: "馬D", MARK_REASON: "市場の見立てより来ると見る度合いが1位"},
        {MARK: "消", HORSE_NO: 7, HORSE_NAME: "馬E", MARK_REASON: ""},     # 理由が空なら添えない
    ])
    assert MarkLines().lines(table) == [
        "◎ 9 馬A：単勝の期待値が1位",
        "○ 2 馬B",
        "☆ 5 馬C：穴馬の中で複勝の期待値が1位",
        "注 6 馬D：市場の見立てより来ると見る度合いが1位",
        "消 7 馬E",
    ]
