"""消の線の研究の道具（``danger_lines.py``）のテスト。値は架空。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_ROOT / "research" / "AIとロジックの予想" / "analysis"), str(_ROOT / "tools")]

import danger_lines  # noqa: E402
from 今週の予想.danger_picker import MARKED_BANDS  # noqa: E402

_LINES = {"1番人気": danger_lines.BandRule(0.12), "4〜5番人気": danger_lines.BandRule(0.04)}


def _favorites() -> pd.DataFrame:
    """3レース。a は1番人気が線以上、b は 4〜5番人気の2頭が線以上、c はどの馬も線未満。"""
    return pd.DataFrame({
        "race_id": ["a", "a", "b", "b", "b", "c", "c"],
        "favorite_band": ["1番人気", "4〜5番人気", "1番人気", "4〜5番人気", "4〜5番人気", "1番人気", "2〜3番人気"],
        "danger_score": [0.13, 0.09, 0.10, 0.05, 0.07, 0.11, 0.20],
    })


def test_いちばん優先する人気帯は本番と同じ() -> None:
    assert danger_lines.FIRST_BAND == MARKED_BANDS[0]


def test_1番人気が線以上ならその馬だけを消にする() -> None:
    assert danger_lines.picked(_favorites(), _LINES)[:2].tolist() == [True, False]


def test_1番人気が線未満なら線をいちばん大きく超えた馬を消にする() -> None:
    assert danger_lines.picked(_favorites(), _LINES)[2:5].tolist() == [False, False, True]


def test_線の無い人気帯と線未満の馬は消にしない() -> None:
    assert danger_lines.picked(_favorites(), _LINES)[5:].tolist() == [False, False]
    assert danger_lines.picked(_favorites(), {"1番人気": danger_lines.BandRule(0.12)}).tolist() == [True, False, False, False, False, False, False]


def test_決まりの組ごとの消の成績は期間と人気帯ごとに数える() -> None:
    favorites = _favorites().assign(race_date="2025-10-04", finish=[1, 5, 2, 4, 3, 9, 1], win_payout=[300.0, None, None, None, None, None, 500.0],
                                    place_payout=[120.0, None, 150.0, None, 200.0, None, 180.0])
    made = danger_lines.rule_set_table(favorites, _LINES).set_index(["期間", "人気帯"])
    assert made.loc[("作る", "1番人気")].tolist() == [1, 1.0, 1.0, 3.0, 1.2]
    assert made.loc[("作る", "4〜5番人気")].tolist() == [1, 0.0, 1.0, 0.0, 2.0]


def test_全頭の予想を足す決まりは市場より低く見る度合いを点に足す() -> None:
    horses = pd.DataFrame({"danger_score": [0.03, 0.03], "market_top3": [0.40, 0.40], "probability": [0.30, 0.38]})
    assert (danger_lines.BandRule(0.08, with_form=True).margin(horses) >= 0).tolist() == [True, False]


def test_1着の予想が市場以上の馬は危険にしない決まり() -> None:
    horses = pd.DataFrame({"danger_score": [0.15, 0.15], "win_probability": [0.20, 0.30], "market_win": [0.25, 0.25]})
    assert (danger_lines.BandRule(0.12, win_below_market=True).margin(horses) >= 0).tolist() == [True, False]
