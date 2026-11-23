"""TrifectaPicker（勝つ確率の予想と世間の見立てから 3連単の買い目を選ぶ）のテスト。確率は架空。"""

from __future__ import annotations

import pytest

from ばんえいの予想.trifecta_picker import TrifectaPicker

_NUMBERS = [1, 2, 3, 4, 5, 6, 7]
_EVEN = [1 / 7] * 7
_MODEL = [0.40, 0.25, 0.15, 0.05, 0.05, 0.05, 0.05]


def test_予想と世間の見立てが同じなら_買う組は無い() -> None:
    assert TrifectaPicker().pick(_NUMBERS, _EVEN, _EVEN) == []


def test_頭数が7頭に足りなければ_買う組は無い() -> None:
    model = [0.5, 0.2, 0.1, 0.1, 0.05, 0.05]
    crowd = [1 / 6] * 6
    assert TrifectaPicker().pick(_NUMBERS[:6], model, crowd) == []


def test_予想が世間の見立てより高い組だけを_ずれの大きい順に() -> None:
    picks = TrifectaPicker().pick(_NUMBERS, _MODEL, _EVEN)
    assert picks[0].order == (1, 2, 3)
    assert picks[0].probability == pytest.approx(0.40 * 0.25 / 0.60 * 0.15 / 0.35)
    assert picks[0].gap == pytest.approx(picks[0].probability / (1 / 7 * 1 / 6 * 1 / 5))
    assert picks[0].strong
    assert [pick.gap for pick in picks] == sorted((pick.gap for pick in picks), reverse=True)
    assert all(pick.probability >= 0.01 and pick.gap >= 1.5 for pick in picks)


def test_線を変えると_買う組が変わる() -> None:
    loose = TrifectaPicker(min_probability=0.001, min_gap=1.0).pick(_NUMBERS, _MODEL, _EVEN)
    assert len(loose) > len(TrifectaPicker().pick(_NUMBERS, _MODEL, _EVEN))
