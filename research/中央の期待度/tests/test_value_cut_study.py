"""見送りの線の研究（ValueCutStudy）と全レースの選び方の探し方（RuleSearch）を、架空の値で確かめる。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from 中央の期待度.analysis.rule_search import Combo, Rule, RuleSearch  # noqa: E402
from 中央の期待度.analysis.value_cut_study import CUTS, SHARES, WEIGHTS, ValueCutStudy, meets, rates_of  # noqa: E402


def _rates(backs: list[float], wins: list[float]) -> dict:
    return {grade: (win, back, 0.9, 10) for grade, back, win in zip("SABC", backs, wins, strict=True)}


def test_条件は全等級で100超えと勝率の順() -> None:
    assert meets(_rates([1.01, 1.2, 1.1, 1.3], [0.4, 0.3, 0.2, 0.1]))   # 回収率の順は問わない
    assert not meets(_rates([1.01, 1.2, 1.1, 0.99], [0.4, 0.3, 0.2, 0.1]))
    assert not meets(_rates([1.1, 1.2, 1.1, 1.3], [0.3, 0.3, 0.2, 0.1]))


def test_率は等級ごとに見送りも数える() -> None:
    part = pd.DataFrame({"finish": [1, 4, 1, 5], "win_payout": [300, 0, 500, 0], "place_payout": [120, 0, 200, 0]})
    rates = rates_of(part, np.array(["S", "S", "見送り", "見送り"]))
    assert rates["S"] == (0.5, 1.5, 0.6, 2) and rates["見送り"] == (0.5, 2.5, 1.0, 2)


def _tops() -> pd.DataFrame:
    rows = []
    for year in (2023, 2024, 2025):
        for i in range(60):
            value = 0.75 + i * 0.01
            win = i % 3 == 0
            rows.append({"year": year, "win_probability": 0.1 + (i % 7) * 0.03, "win_value": value, "finish": 1 if win else 5,
                         "win_payout": 400 if win else 0, "place_payout": 150 if win else 0})
    return pd.DataFrame(rows)


def test_全部の組を出し_本番の決まりで見送りの行がある(tmp_path: Path) -> None:
    study = ValueCutStudy(_tops(), [2023, 2024])
    assert len(study.results()) == len(CUTS) * len(WEIGHTS) * len(SHARES)
    production = study.production()
    assert set(production["期待度"]) >= {"見送り"} and production["期間"].iloc[0] == "探す期間"
    text = study.write(tmp_path / "見送りの線-当日.md").read_text(encoding="utf-8")
    assert "2. 本番の決まりの期間・年ごとの成績" in text and "1. 見送りの線 × 重み × 等級の割合" in text


def test_全レースの選び方は条件に合う馬からレースごとに1頭を選ぶ() -> None:
    rows = pd.DataFrame([
        {"race_id": "R1", "year": 2023, "mark": "◎", "win_probability": 0.30, "market_win": 0.25, "win_odds": 3.0, "popularity": 1, "finish": 1, "win_payout": 300, "place_payout": 110},
        {"race_id": "R1", "year": 2023, "mark": "○", "win_probability": 0.10, "market_win": 0.05, "win_odds": 15.0, "popularity": 5, "finish": 4, "win_payout": 0, "place_payout": 0},
        {"race_id": "R1", "year": 2023, "mark": "消", "win_probability": 0.50, "market_win": 0.50, "win_odds": 1.8, "popularity": 2, "finish": 2, "win_payout": 0, "place_payout": 100},
    ])
    search = RuleSearch(rows, [2023])
    chosen, _ = search.tops(Rule(0.0, 1.0, 1.0, 1000.0, False))   # 期待値 0.9 と 1.5 → 15倍の馬（消は選ばない）
    assert rows.loc[rows["mark"] != "消"].reset_index(drop=True).loc[chosen[0], "win_odds"] == 15.0
    chosen, _ = search.tops(Rule(0.0, 0.0, 1.0, 1000.0, False))   # 確率1位 → 3倍の馬
    assert rows.loc[rows["mark"] != "消"].reset_index(drop=True).loc[chosen[0], "win_odds"] == 3.0
    assert not Combo.passes({"S": (0.4, 1.2, 1.0, 1)})
