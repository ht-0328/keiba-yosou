"""的中実績の公開ルール（2段。``PublicRule``）と、その判定（``PublicRulePicker`` の決め方）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd
import pytest

from 今週の予想.public_rule import PublicRule
from 今週の予想.public_rule_picker import PublicRulePicker


def _forecast(judged: dict | None, timing: str = "当日", marked_top: int = 5) -> dict:
    return {"timing": timing, "public_rule": judged, "horses": [{"mark": "◎", "horse_no": marked_top}, {"mark": "○", "horse_no": 3}]}


def _judged(value: float, top: int = 5) -> dict:
    return {"ready": True, "top": top, "value": value, "probability": 0.3, "odds": 4.2, "partners": [3, 8, 11], "line": 1.25,
            "shobu": value >= 1.25, "reason": ""}


def test_勝負のレースは単勝と馬単の流しを出し_精算の点もそろう() -> None:
    rule = PublicRule.of(_forecast(_judged(1.31)))
    assert rule.lines() == ["公開ルール（全レース）: 単勝 5 100円",
                            "公開ルール（勝負）: 単勝 5 100円 ／ 馬単 1着流し 5 → 3・8・11 各 100円（4点 400円。直した ◎ の期待値 1.31）"]
    assert rule.stakes_all() == [("単勝", "05", 100)]
    assert rule.stakes_shobu() == [("単勝", "05", 100), ("馬単", "0503", 100), ("馬単", "0508", 100), ("馬単", "0511", 100)]


def test_勝負でないレースは全レースの単勝だけ_印の本命と違えばそう添える() -> None:
    rule = PublicRule.of(_forecast(_judged(1.05, top=7)))
    assert rule.lines() == ["公開ルール（全レース）: 単勝 7 100円（印の ◎ 5 とは別の馬）",
                            "公開ルール（勝負）: なし（直した ◎ の期待値 1.05。1.25 以上で勝負）"]
    assert rule.stakes_shobu() == []


def test_判定できないときは2段ともなしと理由() -> None:
    not_ready = PublicRule.of(_forecast({"ready": False, "line": 1.25, "reason": "単勝・複勝・馬連のオッズがそろわない"}))
    assert not_ready.lines() == ["公開ルール（全レース）: なし（単勝・複勝・馬連のオッズがそろわない）",
                                 "公開ルール（勝負）: なし（単勝・複勝・馬連のオッズがそろわない）"]
    assert not_ready.stakes_all() == [] and not_ready.stakes_shobu() == []
    assert PublicRule.of(_forecast(None)).reason == "この予想には入っていない（前の版の予想）"
    assert PublicRule.of(_forecast(_judged(1.4), timing="前日")).reason == "当日の予想で判定する"


def test_直した本命は30倍以下で評価できる馬の期待値1位_相手は直した確率の上位3頭() -> None:
    horses = pd.DataFrame({"horse_no": [1, 2, 3, 4, 5], "win_odds": [2.0, 40.0, 6.0, 8.0, 12.0], "unrated": [False, False, False, True, False],
                           "corrected": [0.40, 0.10, 0.20, 0.20, 0.09]})
    judged = PublicRulePicker.decide(horses)
    # 期待値は 1番 0.8・3番 1.2・5番 1.08。2番は 40倍、4番は評価できないので ◎ の候補にしない（相手には入る）
    assert judged["top"] == 3 and judged["value"] == pytest.approx(1.2) and not judged["shobu"]
    assert judged["partners"] == [1, 4, 2]
