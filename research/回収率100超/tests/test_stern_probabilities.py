"""着順の確率（Harville / Stern）のテスト。架空の勝率だけを使う。"""

from __future__ import annotations

import numpy as np
import pytest

from 回収率100超.analysis.market import SternProbabilities

HARVILLE = SternProbabilities(1.0, 1.0)


def test_1着と2着の確率は組ごとに向きがある() -> None:
    p = np.array([0.6, 0.3, 0.1])
    pair = HARVILLE.ordered_pair(p)
    assert pair[0, 1] > pair[1, 0]


def test_2着の確率はレース全体で合計1になる() -> None:
    p = np.array([0.4, 0.3, 0.2, 0.1])
    pair = HARVILLE.ordered_pair(p)
    assert pair.sum() == pytest.approx(1.0)


def test_3着までの並びの確率もレース全体で合計1になる() -> None:
    p = np.array([0.4, 0.3, 0.2, 0.1])
    assert HARVILLE.ordered_triple(p).sum() == pytest.approx(1.0)


def test_3着以内の確率は全馬を足すと3になる() -> None:
    p = np.array([0.35, 0.25, 0.2, 0.15, 0.05])
    assert HARVILLE.top_three(p).sum() == pytest.approx(3.0)


def test_2着以内の確率は全馬を足すと2になる() -> None:
    p = np.array([0.35, 0.25, 0.2, 0.15, 0.05])
    assert HARVILLE.quinella(p).sum(axis=1).sum() == pytest.approx(2.0)


def test_Stern_の補正は人気馬の3着以内率を下げる() -> None:
    p = np.array([0.6, 0.2, 0.1, 0.06, 0.04])
    harville = HARVILLE.top_three(p)
    stern = SternProbabilities(0.8, 0.7).top_three(p)
    assert stern[0] < harville[0]


def test_同じ馬が重なる組は確率0() -> None:
    p = np.array([0.5, 0.3, 0.2])
    table = HARVILLE.ordered_triple(p)
    assert table[0, 0, 1] == 0.0
    assert table[0, 1, 0] == 0.0
