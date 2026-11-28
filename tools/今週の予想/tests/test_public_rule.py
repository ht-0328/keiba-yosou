"""的中実績の公開ルール（◎ の単勝）の判定のテスト。値は架空。"""

from __future__ import annotations

from 今週の予想.public_rule import PublicRule


def _forecast(value: float | None, odds: float | None, timing: str = "当日") -> dict:
    return {"timing": timing, "horses": [
        {"mark": "○", "horse_no": 3, "win_value": 1.5, "win_odds": 2.0},
        {"mark": "◎", "horse_no": 5, "win_value": value, "win_odds": odds},
    ]}


def test_buys_top_win_when_value_and_odds_are_in_line() -> None:
    rule = PublicRule.of(_forecast(1.04, 4.2))
    assert rule.buys
    assert rule.line() == "公開ルール（◎ の単勝）: 単勝 5 100円"
    assert rule.stakes() == [("単勝", "05", 100)]


def test_lines_are_inclusive() -> None:
    assert PublicRule.of(_forecast(1.0, 6.0)).buys


def test_skips_when_odds_over_cap() -> None:
    rule = PublicRule.of(_forecast(1.2, 6.1))
    assert not rule.buys
    assert rule.line() == "公開ルール（◎ の単勝）: なし（◎ の単勝が 6倍を超える）"
    assert rule.stakes() == []


def test_skips_when_value_under_line() -> None:
    assert PublicRule.of(_forecast(0.99, 3.0)).reason == "◎ の単勝の期待値が 1.00 未満"


def test_skips_without_odds_or_top_or_race_day() -> None:
    assert PublicRule.of(_forecast(None, None)).reason == "◎ の単勝オッズが無い"
    assert PublicRule.of(_forecast(float("nan"), 3.0)).reason == "◎ の単勝オッズが無い"
    assert PublicRule.of({"timing": "当日", "horses": []}).reason == "◎ がいない"
    assert PublicRule.of(_forecast(1.2, 3.0, timing="前日")).reason == "当日の予想で判定する"
