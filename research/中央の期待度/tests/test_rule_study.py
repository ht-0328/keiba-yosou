"""◎ の選び方の候補（TopRule）と、組の比べ方（RuleStudy・PairResult）を、架空の全頭の行で確かめる。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from 中央の期待度.analysis.rule_study import PairResult, RuleStudy  # noqa: E402
from 中央の期待度.analysis.top_rules import RULES  # noqa: E402

_RULES = {rule.key: rule for rule in RULES}


def _race(race_id: str, horses: list[dict], year: int = 2023) -> list[dict]:
    base = {"race_id": race_id, "race_date": pd.Timestamp(f"{year}-05-01"), "year": year, "popularity": 1, "finish": 5,
            "win_payout": 0, "place_payout": 0, "mark": "－", "market_win": 0.1, "win_value_lightgbm": 1.0, "win_value_catboost": 1.0}
    return [{**base, **horse} for horse in horses]


def _rows() -> pd.DataFrame:
    # 馬1: 5倍・確率 0.24（期待値 1.2）、馬2: 40倍・確率 0.04（期待値 1.6）、馬3: 2倍・危険な人気馬（期待値 1.8 だが消）
    return pd.DataFrame(_race("R1", [
        {"horse_no": 1, "win_odds": 5.0, "win_probability": 0.24, "win_value": 1.2, "mark": "◎", "market_win": 0.16,
         "win_value_lightgbm": 0.9, "win_value_catboost": 1.3},
        {"horse_no": 2, "win_odds": 40.0, "win_probability": 0.04, "win_value": 1.6, "market_win": 0.02},
        {"horse_no": 3, "win_odds": 2.0, "win_probability": 0.9, "win_value": 1.8, "mark": "消", "market_win": 0.45},
        {"horse_no": 4, "win_odds": 8.0, "win_probability": 0.13, "win_value": 1.04, "market_win": 0.10,
         "win_value_lightgbm": 1.05, "win_value_catboost": 1.02},
    ]))


def test_上限を外すと期待値1位の大穴を選び_消は選ばない() -> None:
    assert _RULES["今"].tops(_rows())["win_odds"].tolist() == [5.0]
    assert _RULES["上限なし"].tops(_rows())["win_odds"].tolist() == [40.0]
    assert _RULES["上限50"].tops(_rows())["win_odds"].tolist() == [40.0]
    assert _RULES["上限10"].tops(_rows())["win_odds"].tolist() == [5.0]


def test_寄せると確率と期待値も寄せた値を返す() -> None:
    top = _RULES["寄せ0.5"].tops(_rows()).iloc[0]
    assert top["win_odds"] == 5.0
    assert top["win_probability"] == pytest.approx(0.20) and top["win_value"] == pytest.approx(1.0)


def test_2モデル一致の馬がいればその馬を優先する() -> None:
    assert _RULES["2モデル一致"].tops(_rows())["win_odds"].tolist() == [8.0]


def _rates(backs: list[float], wins: list[float]) -> dict[str, dict[str, float]]:
    return {grade: {"勝率": win, "単勝回収率": back, "複勝回収率": 0.9} for grade, back, win in zip("SABC", backs, wins, strict=True)}


def test_条件はどの等級も100超えで勝率と単勝回収率がSからCの順() -> None:
    assert PairResult.passes(_rates([1.3, 1.2, 1.1, 1.01], [0.4, 0.3, 0.2, 0.1]))
    assert not PairResult.passes(_rates([1.3, 1.2, 1.1, 0.99], [0.4, 0.3, 0.2, 0.1]))   # C が 100% 未満
    assert not PairResult.passes(_rates([1.1, 1.2, 1.1, 1.01], [0.4, 0.3, 0.2, 0.1]))   # S < A
    assert not PairResult.passes({"S": _rates([1.3, 1.2, 1.1, 1.01], [0.4, 0.3, 0.2, 0.1])["S"]})   # 等級が欠けている
    assert PairResult.lowest(_rates([1.3, 1.2, 1.1, 0.95], [0.4, 0.3, 0.2, 0.1])) == 0.95


def test_表を書き_満たす組が無ければいちばん近い組を示す(tmp_path: Path) -> None:
    rows = []
    for year in (2023, 2024, 2025):
        for i in range(30):
            rows += _race(f"{year}-{i}", [{"horse_no": 1, "win_odds": 4.0, "win_probability": 0.2 + i * 0.005, "win_value": 0.8 + i * 0.02,
                                           "mark": "◎", "finish": 1 if i % 4 == 0 else 6, "win_payout": 400 if i % 4 == 0 else 0}], year)
    study = RuleStudy(pd.DataFrame(rows), [2023, 2024], rules=[_RULES["今"]], weights=[1.0, 3.0])
    chosen, nearest = study.choose(study.results())
    assert chosen is None and nearest.rule.key == "今"
    text = study.write(tmp_path / "◎の選び方-当日.md").read_text(encoding="utf-8")
    assert "（いちばん近い）" in text and "2023〜2024年 単勝回収率 S/A/B/C" in text
