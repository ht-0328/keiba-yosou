"""Recommendation・RecommendationSet（推奨買目の点とまとまり）のテスト。"""

from __future__ import annotations

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet


def _row(ticket: str, *numbers: int) -> Recommendation:
    return Recommendation(ticket, tuple(numbers), odds=10.0, probability=0.12, value=1.2)


def test_組の表示は_着順の付く券種だけ矢印():
    assert _row("単勝", 6).label == "6"
    assert _row("枠連", 3, 5).label == "3-5"
    assert _row("馬単", 6, 10).label == "6→10"
    assert _row("3連単", 6, 10, 8).label == "6→10→8"


def test_券種の順にまとめ_合計を数え_同じ組は1度だけ足す():
    chosen = RecommendationSet((_row("3連単", 6, 10, 8), _row("単勝", 6), _row("枠連", 4, 8), _row("枠連", 3, 5)))
    assert chosen.lines() == ["単勝 6", "枠連 3-5・4-8", "3連単 6→10→8"]
    assert chosen.points == 4 and chosen.yen == 400 and not chosen.none
    merged = chosen.merged([_row("単勝", 6), _row("複勝", 3)])
    assert merged.lines() == ["単勝 6", "複勝 3", "枠連 3-5・4-8", "3連単 6→10→8"] and merged.points == 5


def test_点が無ければ理由を持つ():
    empty = RecommendationSet((), "11頭未満のレース（8頭）は推奨買目の対象外")
    assert empty.none and empty.lines() == [] and empty.yen == 0
    assert empty.merged([_row("単勝", 6)]).reason == "11頭未満のレース（8頭）は推奨買目の対象外"
