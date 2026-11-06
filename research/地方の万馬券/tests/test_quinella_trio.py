"""馬連と3連複の買い方の部品（買い方の候補・置き場所・成績の表）を架空の値で確かめる。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 地方の万馬券.analysis.quinella_trio.rule import TOP_FORM, QuinellaTrioRule
from 地方の万馬券.analysis.quinella_trio.rule_catalog import stage1, stage1_by_ev, stage2, stage3
from 地方の万馬券.analysis.quinella_trio.rule_study import RuleStudy
from 地方の万馬券.analysis.quinella_trio.ticket_tables_builder import EV_FORWARD, FORM, HAS_TOP, P_FORWARD, TOP_VALUE
from 地方の万馬券.analysis.quinella_trio.ticket_tables_store import QuinellaTrioTablesStore
from 地方の推奨買目.position_model import EV, PROBABILITY

_RACE = 2024010145110101


def _table() -> pd.DataFrame:
    rows = []
    for year, race in ((2024, _RACE), (2025, _RACE + 10000_0000_0000), (2026, _RACE + 20000_0000_0000)):
        for a, b, p, odds, payout, form, top in ((1, 2, 0.30, 4.0, 400, "人人", True), (1, 5, 0.10, 12.0, 0, "人中", True),
                                                 (2, 8, 0.04, 40.0, 0, "人大", False), (5, 8, 0.02, 80.0, 0, "中大", False)):
            rows.append({"race_id": race, "a": a, "b": b, PROBABILITY: p, "odds": odds, "payout": payout, EV: p * odds,
                         P_FORWARD: p if year > 2024 else float("nan"), EV_FORWARD: p * odds if year > 2024 else float("nan"),
                         "year": year, "race_date": f"{year}-01-01", "field_size": 10, FORM: form, HAS_TOP: top, TOP_VALUE: 1.1})
    return pd.DataFrame(rows)


def test_買い方は_帯と線と頭数と形と上限で選ぶ():
    table = _table()
    assert len(QuinellaTrioRule("馬連", 1.0, 0.0, 20.0).choose(table)) == 6            # 1-2（1.2）と 1-5（1.2）が 3年ぶん
    assert len(QuinellaTrioRule("馬連", 1.0, 0.0, 20.0, min_heads=11).choose(table)) == 0
    assert list(QuinellaTrioRule("馬連", 1.0, top_k=1).choose(table)["a"].unique()) == [1]  # 確率の順なら 1-2
    assert set(QuinellaTrioRule("馬連", 1.0, form=TOP_FORM).choose(table)[FORM]) == {"人人", "人中"}
    assert set(QuinellaTrioRule("馬連", 1.0, form="人大|中大").choose(table)[FORM]) == {"人大", "中大"}
    assert QuinellaTrioRule("3連複", 1.05, 20.0, 300.0, 8, 3, form="人中大").label == "20〜300倍・期待値 1.05 以上・8頭以上・確率の上位 3 点・型 人中大"


def test_荒れ具合の条件は_列があるときだけ効く():
    table = _table()
    rule = QuinellaTrioRule("馬連", 1.0, upset_column="中荒れ以上の確率", upset_min=0.5)
    assert len(rule.choose(table)) == len(QuinellaTrioRule("馬連", 1.0).choose(table))
    upset = pd.DataFrame({"race_id": [str(_RACE)], "中荒れ以上の確率": [0.3], "大荒れ以上の確率": [0.05]})
    study = RuleStudy({"馬連": table, "3連複": table.iloc[0:0]}, {"馬連": upset})
    result = study.evaluate([rule])[0]
    assert "中荒れ以上の確率 0.5" in result.row["買い方"]


def test_成績の表は_年ごとの回収率と判定を持つ():
    study = RuleStudy({"馬連": _table(), "3連複": _table().iloc[0:0]})
    result = study.evaluate([QuinellaTrioRule("馬連", 1.0, 0.0, 20.0)])[0]
    assert result.row["2024年"].startswith("200.0%")            # 1-2 が 400円、1-5 が外れ → 400 / 200
    assert result.row["前の年 2025"] == "200.0%" and result.row["券種"] == "馬連"
    assert result.row["最高の1点を除く"] == "133.3%" and result.passed is True   # 3年とも 200%、最高の1点を除いても 133%
    losing = study.evaluate([QuinellaTrioRule("馬連", 1.0, 30.0, 100.0)])[0]   # 2-8（40倍）だけで外れ
    assert losing.row["2024年"].startswith("0.0%") and losing.passed is False


def test_候補の一覧は_段ごとに決まった数():
    assert len(stage1("馬連")) == 4 * 3 * 2 * 4 and len(stage1_by_ev("馬連")) == 4 * 3 * 2 * 3
    base = QuinellaTrioRule("3連複", 1.0, 20.0, 300.0, 8, 3)
    assert len(stage2(base)) == 9 and all(rule.odds_max == 300.0 for rule in stage2(base))
    assert len(stage3(base)) == 8 and stage3(base)[0].upset_column == "中荒れ以上の確率"


def test_置き場所に書いて読める(tmp_path: Path):
    store = QuinellaTrioTablesStore(tmp_path)
    store.save({"馬連": _table(), "3連複": _table()})
    loaded = store.load()
    assert len(loaded["馬連"]) == 12 and store.path("3連複").is_file()
