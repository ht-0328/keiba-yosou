"""LocalBetRule（推奨買目に全頭の予想の単勝・複勝を足す）のテスト。予想の値は架空。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NO, MARK, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_PROBABILITY, WIN_VALUE

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知.local_bet_rule import LocalBetRule


def _table(top_win_value: float, place_values: tuple[float, ...]) -> pd.DataFrame:
    rows = [{MARK: "◎", HORSE_NO: 7, WIN_ODDS: 3.0, WIN_PROBABILITY: 0.35, WIN_VALUE: top_win_value, PROBABILITY: 0.78, PLACE_VALUE: place_values[0]}]
    rows += [{MARK: "－", HORSE_NO: no, WIN_ODDS: 20.0, WIN_PROBABILITY: 0.03, WIN_VALUE: 0.5, PROBABILITY: 0.26, PLACE_VALUE: value}
             for no, value in enumerate(place_values[1:], start=1)]
    return pd.DataFrame(rows)


def _recommended(*rows: Recommendation, reason: str = "") -> RecommendationSet:
    return RecommendationSet(rows, reason)


def test_推奨買目に_本命の単勝と_複勝の期待値1_25以上を足し_同じ組は1度だけ() -> None:
    recommended = _recommended(Recommendation("枠連", (3, 5), 8.0, 0.14, 1.12), Recommendation("単勝", (7,), 3.0, 0.36, 1.08))
    bets = LocalBetRule().pick(_table(1.05, (1.10, 1.30, 0.90)), race_day=True, recommended=recommended)
    assert bets.lines() == ["単勝 7", "複勝 1", "枠連 3-5"]
    assert bets.points == 3 and bets.reason == ""
    place = next(row for row in bets.rows if row.ticket == "複勝")
    assert place.probability == 0.26 and place.value == 1.30 and round(place.odds, 2) == 5.0


def test_推奨買目が無く_線にも届かなければ_なしと理由() -> None:
    bets = LocalBetRule().pick(_table(0.90, (1.02, 0.80)), race_day=True, recommended=_recommended(reason="11頭未満のレース（8頭）は推奨買目の対象外"))
    assert bets.none
    assert bets.reason == "11頭未満のレース（8頭）は推奨買目の対象外。◎ の単勝の期待値 0.90 は 1.00 未満。複勝の期待値 1.25 以上の馬はいない"


def test_推奨買目の理由は_点があっても添える() -> None:
    bets = LocalBetRule().pick(_table(1.05, (1.10,)), race_day=True, recommended=_recommended(reason="11頭未満のレース（8頭）は推奨買目の対象外"))
    assert bets.lines() == ["単勝 7"] and bets.reason == "11頭未満のレース（8頭）は推奨買目の対象外"


def test_前日の時点は買わない() -> None:
    bets = LocalBetRule().pick(_table(1.50, (1.50,)), race_day=False, recommended=_recommended(Recommendation("単勝", (7,), 3.0, 0.4, 1.2)))
    assert bets.none and bets.reason == "馬体重が届く前の前日の時点では買わない"
