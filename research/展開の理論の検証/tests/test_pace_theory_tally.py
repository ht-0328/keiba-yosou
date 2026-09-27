"""先頭率・逃げたい馬の数え方・展開の効き目・馬場状態つきの基準のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 展開の理論の検証.analysis.leaders import LEAD_RATE, LED_RECENTLY, RUNS_BEFORE, EarlyRunHistory, LeaderCountTable
from 展開の理論の検証.analysis.pace import HIGH, SLOW, ConditionPaceMeasure
from 展開の理論の検証.analysis.tally import VARIANTS, MarketWinProbability, PaceEffectScore


def _runs(ranks: list[int | None], styles: list[str]) -> pd.DataFrame:
    """1頭の馬の、古い順の走。"""
    count = len(ranks)
    return pd.DataFrame({
        "race_id": [f"R{i}" for i in range(count)], "race_date": pd.date_range("2025-01-01", periods=count, freq="14D"),
        "horse_id": "H1", "surface": "芝", "field_size": 11, "first_corner_rank": pd.array(ranks, dtype="Int32"),
        "style": styles, "style_before": None,
    })


def test_先頭率は今回より前の走だけから作る() -> None:
    history = EarlyRunHistory().build(_runs([1, 5, 1, 3], ["逃げ", "差し", "逃げ", "先行"]))
    assert np.isnan(history[LEAD_RATE].iloc[0])
    assert history[LEAD_RATE].iloc[1] == pytest.approx(1.0)
    assert history[LEAD_RATE].iloc[3] == pytest.approx(2 / 3)
    assert history[LED_RECENTLY].tolist() == [0, 1, 1, 2]
    assert history[RUNS_BEFORE].tolist() == [0, 1, 2, 3]


def test_最初のコーナーの記録が無い走は先頭率に数えない() -> None:
    history = EarlyRunHistory().build(_runs([1, None, 2], ["逃げ", "逃げ", "先行"]))
    assert history[LEAD_RATE].iloc[2] == pytest.approx(1.0)


def test_逃げたい馬はレースごとに数える() -> None:
    runners = pd.DataFrame({
        "race_id": ["A", "A", "A", "B"], "style_before": ["逃げ", "先行", None, "逃げ"],
        LEAD_RATE: [0.6, 0.4, np.nan, 0.2], "先頭率（同じ芝ダの近5走）": [0.6, 0.2, np.nan, 0.2],
        LED_RECENTLY: [2, 1, 0, 0], RUNS_BEFORE: [5, 2, 0, 4],
    })
    counts = LeaderCountTable().build(runners).set_index("race_id")
    assert counts.loc["A", "推定脚質が逃げ"] == 1
    assert counts.loc["A", "先頭率0.4以上"] == 2
    assert counts.loc["A", "同じ芝ダの先頭率0.4以上・3走以上"] == 1
    assert counts.loc["A", "先頭率の合計"] == pytest.approx(1.0)
    assert counts.loc["B", "近3走で逃げた"] == 0


def test_オッズから見た勝率はレースで合計1() -> None:
    runners = pd.DataFrame({"race_id": ["A", "A", "A"], "win_odds": [2.0, 4.0, 4.0]})
    assert MarketWinProbability().build(runners)["オッズから見た勝率"].tolist() == pytest.approx([0.5, 0.25, 0.25])


def test_効き目はスローでの前後の差からハイでの前後の差を引いた値() -> None:
    variant = VARIANTS[0]  # 脚質（結果）
    rows = []
    for pace, front_top3 in ((SLOW, 3), (HIGH, 2)):  # 前の4頭のうち、スローで3頭・ハイで2頭が3着以内
        rows += [{"ペース": pace, variant.name: "逃げ", "finish": 1 if i < front_top3 else 9} for i in range(4)]
        rows += [{"ペース": pace, variant.name: "差し", "finish": 9} for _ in range(4)]
    runners = pd.DataFrame(rows).assign(win_payout=0, place_payout=0, オッズから見た勝率=0.1)
    score = PaceEffectScore().score(runners, "ペース", variant)
    assert score["前−後ろ 複勝率 スロー"] == pytest.approx(75.0)
    assert score["効き目（複勝率）"] == pytest.approx(25.0)


def test_馬場状態ごとの基準が作れなければ馬場状態を分けない基準で補う() -> None:
    count = 41
    races = pd.DataFrame({
        "race_id": [f"R{i:03d}" for i in range(count)],
        "race_date": pd.date_range("2024-01-01", periods=count, freq="7D"),
        "venue_code": "05", "track_code": "23", "distance_m": 1600, "class_order": 3,
        "condition": ["良"] * (count - 1) + ["不良"],
        "t": 35.0 + np.tile([-0.5, 0.5], count // 2 + 1)[:count],
    })
    z = ConditionPaceMeasure("t").z(races)
    assert not np.isnan(z.iloc[-1])
