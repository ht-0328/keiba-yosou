"""地方の印の買い目の研究の部品を、架空の値で確かめる（実DB は使わない）。"""

from __future__ import annotations

import pandas as pd

from 地方の印の買い目.analysis.mark_combos import split_combo
from 地方の印の買い目.analysis.mark_plan import PER_RACE, MarkPlan
from 地方の印の買い目.analysis.plan_summary import PlanSummary
from 地方の印の買い目.analysis.reverse_combos import REVERSE_RULE, ReverseCombos

_RACE = 2024010145110101


def _source(rows: list[tuple[str, str, int, float, float, object]]) -> pd.DataFrame:
    return pd.DataFrame([{"race_id": _RACE, "race_date": "2024-01-01", "top_band": "1.00 以上", "rule": rule, "ticket": ticket, "combo": combo,
                          "odds": odds, "payout": payout, "reason": reason} for rule, ticket, combo, odds, payout, reason in rows])


def test_組番は券種の頭数で馬番に分ける():
    table = split_combo(_source([("単勝", "単勝", 3, 4.4, 0.0, None), ("馬単", "馬単", 301, 9.6, 960.0, None),
                                 ("3連単（◎→○▲☆→○▲△☆）", "3連単", 30104, 101.6, 0.0, "トリガミ")]))
    assert table[["a", "b", "c"]].values.tolist() == [[3, 0, 0], [3, 1, 0], [3, 1, 4]]
    assert table["dropped"].tolist() == [False, False, True]


def test_裏は馬単の1着と2着を入れ替えオッズと払戻を空にする():
    marks = split_combo(_source([("馬単", "馬単", 301, 9.6, 960.0, None), ("馬連", "馬連", 103, 4.5, 0.0, None)]))
    reverse = ReverseCombos().of(marks)
    assert len(reverse) == 1 and reverse.loc[0, "rule"] == REVERSE_RULE
    assert (reverse.loc[0, "a"], reverse.loc[0, "b"]) == (1, 3) and pd.isna(reverse.loc[0, "odds"])


def _table() -> pd.DataFrame:
    rows = [("単勝", 4.0, 0.30, 400.0), ("馬単", 10.0, 0.12, 0.0), ("馬単", 20.0, 0.04, 0.0)]
    return pd.DataFrame([{"race_id": _RACE, "year": 2024, "race_date": "2024-01-01", "field_size": 10, "top_band": "1.00 以上", "rule": rule,
                          "dropped": False, "odds": odds, "P": p, "ev": p * odds, "payout": payout} for rule, odds, p, payout in rows])


def test_点ごとは期待値の線以上の点を1点100円で買う():
    chosen = MarkPlan("線 1.1", ("単勝", "馬単"), ev_min=1.1).choose(_table())
    assert chosen["rule"].tolist() == ["単勝", "馬単"] and chosen["stake"].tolist() == [100, 100]
    assert chosen["returned"].tolist() == [400.0, 0.0]


def test_レースごとは見込みの回収率が線に届くレースだけ配って買う():
    plan = MarkPlan("レースごと", ("単勝", "馬単"), PER_RACE, line=1.0)
    chosen = plan.choose(_table())
    assert len(chosen) == 3 and chosen["stake"].sum() >= 5000
    win = chosen[chosen["rule"] == "単勝"].iloc[0]
    assert win["returned"] == win["stake"] * 4.0
    assert MarkPlan("線が高い", ("単勝", "馬単"), PER_RACE, line=1.5).choose(_table()).empty


def test_成績は回収率と最高の1点を除いた回収率を出す():
    chosen = pd.DataFrame({"race_id": [_RACE, _RACE + 1], "race_date": ["2024-01-01", "2024-01-02"], "stake": [100, 100],
                           "returned": [300.0, 0.0], "ev": [1.2, 0.8]})
    row = PlanSummary().row("例", "2024年", chosen, 2)
    assert row["回収率"] == "150.0%" and row["最高の1点を除く回収率"] == "0.0%" and row["見込みの回収率"] == "100.0%"
    assert row["的中レース"] == 1 and row["勝った日の割合"] == "50.0%"
