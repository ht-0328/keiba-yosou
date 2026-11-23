"""消のロジックの研究の道具（``danger_cancel.py``・``danger_tickets.py``）のテスト。値は架空。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_ROOT / "research" / "AIとロジックの予想" / "analysis"), str(_ROOT / "tools")]

import danger_cancel  # noqa: E402
import danger_tickets  # noqa: E402
from 今週の予想.danger_cancel_logic import DangerCancelLogic  # noqa: E402


def _dangers() -> pd.DataFrame:
    """作る期間の消が4頭。1着の予想が市場の見立て以上は2頭（1頭が1着）。"""
    return pd.DataFrame({"race_date": ["2025-10-04"] * 4, "is_danger": [True] * 4, "win_probability": [0.30, 0.25, 0.20, 0.10],
                         "market_win": [0.25, 0.25, 0.25, 0.25], "finish": [1, 5, 2, 9], "win_payout": [400.0, None, None, None]})


def test_取り消す消は本番のロジックと同じ決まりで選ぶ() -> None:
    table = _dangers()
    assert danger_cancel.cancelled(table).tolist() == [True, True, False, False]
    assert danger_cancel.cancelled(table).tolist() == [DangerCancelLogic().cancels(row) for row in table.to_dict("records")]
    assert not danger_cancel.cancelled(table.assign(is_danger=False)).any()


def test_期間ごとに今の消と残る消と取り消す消の成績を出す() -> None:
    made = danger_cancel.summary(_dangers()).set_index(["期間", "消"])
    assert made.loc[("作る", "今の消")].tolist() == [4, 0.25, 0.5, 1.0]
    assert made.loc[("作る", "残る消")].tolist() == [2, 0.0, 0.5, 0.0]
    assert made.loc[("作る", "取り消す消")].tolist() == [2, 0.5, 0.5, 2.0]
    assert made.loc[("確かめる", "今の消"), "頭数"] == 0


def test_買い方ごとの回収率と的中率は1レースを1つに数える() -> None:
    tickets = pd.DataFrame({"買い方": ["馬単"] * 3, "券種": ["馬単"] * 3, "レースID": ["a", "a", "b"], "単位": [1.0, 1.0, 1.0],
                            "払戻（100円あたり）": [0.0, 600.0, 0.0]})
    assert danger_tickets.flat(tickets).loc[("馬単", "馬単")].tolist() == [2, 2.0, 0.5]


def test_印の買い目の1行は買ったレースだけを数える() -> None:
    races = pd.DataFrame({"day": ["2026-01-10", "2026-01-10", "2026-01-11"], "bought": [True, True, False],
                          "stake": [5000, 5000, 0], "back": [12000.0, 0.0, 0.0]})
    assert danger_tickets.line(races) == "買う 2 回収率 120.0% 的中率 50.0% 1日の儲け 1,000円"
    assert danger_tickets.line(races.assign(bought=False)) == "買う 0"
