"""◎と1番人気を比べる部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 一番人気を疑う.analysis.evaluation import ConfidenceBands, DoubtBreakdown, TopPickSummary, TopPickTable


def _predictions() -> pd.DataFrame:
    """2レース・3頭ずつ。r1 は◎が1番人気（3着以内）。r2 は◎が2番人気（着外）で、1番人気が3着以内。"""
    return pd.DataFrame({
        "レースID": ["r1"] * 3 + ["r2"] * 3, "馬番": [1, 2, 3, 1, 2, 3],
        "確定の単勝人気": [1, 2, 3, 2, 1, 3], "3着以内": [1, 0, 1, 0, 1, 1],
        "score": [0.8, 0.3, 0.2, 0.6, 0.5, 0.1], "区切り": ["前半"] * 3 + ["後半"] * 3, "クラス": ["新馬"] * 3 + ["未勝利"] * 3,
    })


def test_レースごとに本命と1番人気を並べる() -> None:
    races = TopPickTable().build(_predictions())
    assert races.loc["r1", "馬番"] == 1 and not races.loc["r1", "疑った"]
    assert races.loc["r2", "馬番"] == 1 and races.loc["r2", "馬番_1番人気"] == 2 and races.loc["r2", "疑った"]


def test_まとめは本命と1番人気の3着以内率と疑ったレースの成績() -> None:
    row = TopPickSummary().row(TopPickTable().build(_predictions()), "例")
    assert row["◎の3着以内率"] == pytest.approx(0.5)
    assert row["1番人気の3着以内率"] == pytest.approx(1.0)
    assert row["差"] == pytest.approx(-0.5)
    assert row["上回った区切り"] == "0 / 2"
    assert row["疑った割合"] == pytest.approx(0.5)
    assert row["疑ったレースの◎"] == pytest.approx(0.0) and row["疑ったレースの1番人気"] == pytest.approx(1.0)


def test_条件ごとに疑ったレースの差を出す() -> None:
    table = DoubtBreakdown().by(TopPickTable().build(_predictions()), "クラス")
    assert table.loc["未勝利", "疑ったレース"] == 1
    assert table.loc["未勝利", "差"] == pytest.approx(-1.0)
    assert table.loc["新馬", "疑った割合"] == pytest.approx(0.0)


def test_本命の確率の帯ごとに分ける() -> None:
    table = ConfidenceBands().table(TopPickTable().build(_predictions()))
    assert list(table.index) == ["0.5〜0.6", "0.7〜0.8"]
    assert table.loc["0.7〜0.8", "◎の3着以内率"] == pytest.approx(1.0)
    assert table.loc["0.5〜0.6", "◎が1番人気の割合"] == pytest.approx(0.0)
