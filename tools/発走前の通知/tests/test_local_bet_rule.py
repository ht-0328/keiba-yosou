"""LocalBetRule（地方で実際に買う買い目）のテスト。予想の値は架空。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, PLACE_VALUE, WIN_VALUE

from 発走前の通知.local_bet_rule import LocalBetRule


def _table(top_win_value: float, place_values: tuple[float, ...]) -> pd.DataFrame:
    rows = [{MARK: "◎", HORSE_NO: 7, HORSE_NAME: "イチバン", WIN_VALUE: top_win_value, PLACE_VALUE: place_values[0]}]
    rows += [{MARK: "－", HORSE_NO: no, HORSE_NAME: f"ウマ{no}", WIN_VALUE: 0.5, PLACE_VALUE: value}
             for no, value in enumerate(place_values[1:], start=1)]
    return pd.DataFrame(rows)


def test_当日は_本命の単勝が1以上と_複勝の期待値1_25以上を_100円ずつ() -> None:
    bets = LocalBetRule().pick(_table(1.05, (1.10, 1.30, 0.90)), race_day=True)
    assert bets.lines == ("単勝 ◎7 イチバン（期待値 1.05）100円", "複勝 1 ウマ1（期待値 1.30）100円")
    assert bets.reasons == ()
    assert bets.text() == ["実際に買う:", *bets.lines]


def test_どちらも線に届かなければ_なしと理由() -> None:
    bets = LocalBetRule().pick(_table(0.90, (1.02, 0.80)), race_day=True)
    assert bets.none
    assert bets.reasons == ("◎ の単勝の期待値 0.90 は 1.00 未満", "複勝の期待値 1.25 以上の馬はいない")
    assert bets.text() == ["買い目: なし（◎ の単勝の期待値 0.90 は 1.00 未満。複勝の期待値 1.25 以上の馬はいない）"]


def test_前日の時点は買わない() -> None:
    bets = LocalBetRule().pick(_table(1.50, (1.50,)), race_day=False)
    assert bets.none
    assert bets.text() == ["買い目: なし（馬体重が届く前の前日の時点では買わない）"]
