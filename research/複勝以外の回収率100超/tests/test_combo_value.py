"""入口④（組の期待値の買い方の線の選び方と、期間ごとの成績）のテスト。値は架空で、DB は使わない。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 複勝以外の回収率100超.analysis import combo_rule_grid
from 複勝以外の回収率100超.analysis.combo_operation_report import ComboOperationReport
from 複勝以外の回収率100超.analysis.combo_period_report import ComboPeriodReport
from 複勝以外の回収率100超.analysis.combo_rule_grid import ComboRuleGrid


def _valued() -> pd.DataFrame:
    """馬単の組。◎ は 1番。1→2 は期待値 1.2・20倍で毎日当たる、2→1 は期待値 1.5・50倍で外れる（◎ が1着でない）。"""
    rows = []
    for day in range(1, 11):
        race = f"r{day}"
        rows.append({"race_id": race, "race_date": f"2025-01-{day:02d}", "expectation": "高", "top": 1, "h1": 1, "h2": 2,
                     "value": 1.2, "odds": 20.0, "hit": True, "payout": 2000.0})
        rows.append({"race_id": race, "race_date": f"2025-01-{day:02d}", "expectation": "低", "top": 1, "h1": 2, "h2": 1,
                     "value": 1.5, "odds": 50.0, "hit": False, "payout": 0.0})
    return pd.DataFrame(rows)


def test_線と上限と対象ごとに数え_幅の下の端の高い順に並べる(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(combo_rule_grid, "MIN_HITS", 5)
    table = ComboRuleGrid().table(TicketType.EXACTA, _valued())
    best = table.iloc[0]
    assert best["回収率"] == pytest.approx(2000.0) and best["点数"] == 10   # 1→2 だけを買う組み合わせ（◎ が1着・線 1.2 以下・上限 30倍）
    everything = table[(table["対象"] == "全") & (table["線"] == 1.0) & (table["上限"] == 100)].iloc[0]
    assert everything["点数"] == 20 and everything["回収率"] == pytest.approx(1000.0)
    assert set(table[table["対象"] == "高◎"]["点数"]) == {10}


def _tickets() -> pd.DataFrame:
    rows = [{"レースID": f"{year}r{at}", "開催日": f"{year}-05-0{at + 1}", "買い方": "馬連（組の期待値）", "払戻（100円あたり）": payout, "外した理由": ""}
            for year, payouts in ((2019, (300.0, 0.0)), (2021, (0.0, 0.0)), (2024, (500.0, 0.0))) for at, payout in enumerate(payouts)]
    rows.append({"レースID": "2024r9", "開催日": "2024-05-09", "買い方": "馬連（組の期待値）", "払戻（100円あたり）": 900.0, "外した理由": "トリガミ"})
    return pd.DataFrame(rows)


def test_期間ごとの成績は外した点を数えず_年ごとの回収率も出す() -> None:
    periods, yearly = ComboPeriodReport().tables(_tickets(), ("馬連（組の期待値）",))
    unseen = periods[periods["期間"].str.startswith("2019〜2020")].iloc[0]
    assert unseen["点数"] == 2 and unseen["的中"] == 1 and unseen["回収率"] == "150.0%"
    whole = periods[periods["期間"].str.startswith("2019〜2026")].iloc[0]
    assert whole["点数"] == 6 and whole["回収率"] == "133.3%"   # 800 ÷ 600。トリガミで外した 900円は数えない
    assert yearly.loc["馬連（組の期待値）", 2021] == 0.0


def test_運用の目安は重みで金額を決め_落ち込みと連敗を数える() -> None:
    lines = ComboOperationReport().lines(_tickets(), {"馬連（組の期待値）": 2.0}, days=6)
    assert lines[0].startswith("- 買うレース: 6") and "平均 1.0 レース" in lines[0]
    assert "回収率: 133.3%" in lines[3]
    assert "いちばん深い落ち込み: 600円" in lines[4]   # 2019年の当たりのあと、4レース続けて外れて 200円 × 3 = 600円 下がる
    assert lines[5] == "- いちばん長い連敗: 3 レース"
