"""理論の一覧・同じ人気の成績・理論の検証の表を、架空の値で確かめる。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from 地方の万馬券.analysis.popularity_band import FAVORITE, LONGSHOT, MIDDLE
from 地方の万馬券.analysis.popularity_baseline import PLACE_RATE, PopularityBaseline
from 地方の万馬券.analysis.runner_circumstances import CIRCUMSTANCES, SUPPORT_RATIO
from 地方の万馬券.analysis.theory_catalog import THEORIES
from 地方の万馬券.analysis.theory_check_table import KEEP, TOO_FEW, WRONG_WAY, TheoryCheckTable
from 地方の万馬券.analysis.theory import FAVORITE_FAILS, LONGSHOT_COMES, Theory


def _table(n: int = 1600) -> pd.DataFrame:
    """2つの期間 × 1番人気と 9番人気。事情「前走3着以内」の 9番人気だけよく来る架空の表。"""
    rng = np.random.default_rng(0)
    half = n // 2
    rows = pd.DataFrame({
        "race_id": [f"r{i // 2}" for i in range(n)],
        "race_date": [date(2020, 6, 1) if i < half else date(2025, 6, 1) for i in range(n)],
        "popularity": [1, 9] * (n // 2), "band": [FAVORITE, LONGSHOT] * (n // 2),
        "prev_popularity": 5, "win_odds": [2.0, 30.0] * (n // 2), SUPPORT_RATIO: 1.0,
    })
    for name in CIRCUMSTANCES:
        rows[name] = False
    rows["前走3着以内"] = rng.random(n) < 0.5
    comes = (rows["band"] == LONGSHOT) & rows["前走3着以内"]
    rows["finish"] = np.where(comes, 2, np.where(rows["band"] == FAVORITE, 1, 9))
    rows["place_payout"] = np.where(rows["finish"] <= 3, np.where(rows["band"] == FAVORITE, 110, 800), 0)
    rows["win_payout"] = np.where(rows["finish"] == 1, 200, 0)
    return rows


def test_理論の条件は全部_bool_の列を返す():
    table = _table()
    for theory in THEORIES:
        applied = theory.applies(table)
        assert applied.dtype == bool and len(applied) == len(table), theory.name


def test_同じ人気の成績は人気ごとの平均を内訳で重み付けする():
    table = _table()
    baseline = PopularityBaseline().fit(table)
    nines = table[table["popularity"] == 9]
    assert abs(baseline.expected(nines)[PLACE_RATE] - (nines["finish"] <= 3).mean()) < 1e-9
    mixed = table.iloc[:2]      # 1番人気（複勝率 1.0）と 9番人気が1頭ずつ
    assert baseline.expected(mixed)[PLACE_RATE] == (1.0 + (nines["finish"] <= 3).mean()) / 2


def test_理論の検証は向きと頭数で判定する():
    table = _table()
    comes = Theory("前走3着以内", LONGSHOT_COMES, (LONGSHOT,), "", lambda t: t["前走3着以内"])
    fails = Theory("前走3着以内", FAVORITE_FAILS, (FAVORITE,), "", lambda t: t["前走3着以内"])
    rare = Theory("まれ", LONGSHOT_COMES, (MIDDLE,), "", lambda t: t["前走3着以内"])
    result = TheoryCheckTable(date(2024, 1, 1)).build(table, (comes, fails, rare), title="t")
    verdicts = {(row[0], row[1], row[2]): row[15] for row in result.rows}
    assert verdicts[(LONGSHOT_COMES, "前走3着以内", "大穴")] == KEEP          # 来る理論どおり（差が大きく正）
    assert verdicts[(FAVORITE_FAILS, "前走3着以内", "人気馬")] == WRONG_WAY   # 1番人気は全部来るので差 0 → 崩れる向きではない
    assert verdicts[(LONGSHOT_COMES, "まれ", "中穴")] == TOO_FEW
