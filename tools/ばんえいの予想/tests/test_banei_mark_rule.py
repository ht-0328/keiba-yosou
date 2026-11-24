"""BaneiMarkRule（ばんえいの印）と OrderProbabilities（着順の並びの確率）のテスト。確率は架空。"""

from __future__ import annotations

import pytest

from ばんえいの予想.banei_mark_rule import BaneiMarkRule
from ばんえいの予想.order_probabilities import OrderProbabilities

_MODEL = [0.30, 0.20, 0.14, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03]
_CROWD = [0.30, 0.20, 0.14, 0.10, 0.08, 0.06, 0.02, 0.03, 0.07]


def test_勝つ確率の順に印_残りはずれの大きい順に_星と注() -> None:
    marks = BaneiMarkRule().assign(_MODEL, _CROWD)
    assert [mark for mark, _ in marks] == ["◎", "○", "▲", "△", "△", "△", "☆", "注", "－"]
    assert marks[0][1] == "勝つ確率がレース内1位（30%）"
    assert marks[6][1].startswith("印の無い馬の中で、予想が世間の見立てを上回る度合いが1位")
    assert marks[1][1] == ""


def test_ずれが線に届かなければ_星と注は付けない() -> None:
    marks = BaneiMarkRule().assign(_MODEL, _MODEL)
    assert [mark for mark, _ in marks][6:] == ["－", "－", "－"]


def test_3着以内の確率は_合計が3で_勝つ確率の順() -> None:
    top3 = OrderProbabilities(_MODEL).top3()
    assert sum(top3) == pytest.approx(3.0)
    assert top3 == sorted(top3, reverse=True)
    assert top3[0] > _MODEL[0]


def test_3頭以下なら_全頭が3着以内() -> None:
    assert OrderProbabilities([0.5, 0.3, 0.2]).top3() == [1.0, 1.0, 1.0]
