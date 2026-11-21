"""理論の一覧・同じ人気の成績・期間の分け方・理論の検証の表を、架空の値で確かめる。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from 高知ファイナルの高配当.analysis.final_runners import FinalRunners
from 高知ファイナルの高配当.analysis.kochi_run_features import KochiRunFeatures
from 高知ファイナルの高配当.analysis.period_split import PeriodSplit
from 高知ファイナルの高配当.analysis.popularity_band import FAVORITE, LONGSHOT
from 高知ファイナルの高配当.analysis.same_popularity_rates import PLACE, WIN, SamePopularityRates
from 高知ファイナルの高配当.analysis.theory import Theory
from 高知ファイナルの高配当.analysis.theory_catalog import GROUPS, THEORIES
from 高知ファイナルの高配当.analysis.theory_check_table import ALL_BANDS, TheoryCheckTable

from .sample_runs import FIELD_SIZE, kochi_runs


def _runners(count: int = 400) -> pd.DataFrame:
    """1番人気と 9番人気が半分ずつ。印 ``flag`` の付いた 9番人気は必ず3着、付かない 9番人気は来ない架空の表。"""
    popularity = [1, 9] * (count // 2)
    flag = [index % 4 == 1 for index in range(count)]
    finish = [1 if pop == 1 else (3 if marked else 9) for pop, marked in zip(popularity, flag)]
    table = pd.DataFrame({
        "race_date": [date(2018, 6, 1) if index < count // 2 else date(2025, 6, 1) for index in range(count)],
        "popularity": popularity, "band": [FAVORITE, LONGSHOT] * (count // 2), "flag": flag, "finish": finish,
    })
    table["placed"] = (table["finish"] <= 3).astype(float)
    table["won"] = (table["finish"] == 1).astype(float)
    table["win_return"] = table["won"] * 2.0
    table["place_return"] = table["placed"] * 1.5
    return table


def test_理論の条件は全部_bool_の列を返す():
    runners = FinalRunners(min_heads=FIELD_SIZE).select(KochiRunFeatures().build(kochi_runs()))
    for theory in THEORIES:
        applied = theory.applies(runners)
        assert applied.dtype == bool and len(applied) == len(runners), theory.name


def test_理論の区分と名前に漏れと重なりが無い():
    assert {theory.group for theory in THEORIES} == set(GROUPS)
    names = [theory.name for theory in THEORIES]
    assert len(names) == len(set(names))


def test_同じ人気の成績は人気ごとの率で見込みの頭数を出す():
    table = _runners()
    rates = SamePopularityRates().fit(table)
    nines = table[table["popularity"] == 9]
    assert rates.expected(nines, PLACE) == nines["placed"].sum()
    assert rates.expected(table.iloc[:2], WIN) == 1.0            # 1番人気（勝率 1）と 9番人気（勝率 0）が1頭ずつ


def test_期間は区切りの日で分かれ_名前は実際にある年():
    days = pd.Series(pd.to_datetime(["2016-05-01", "2019-12-31", "2020-01-01", "2023-06-01", "2024-01-01", "2026-03-01"]))
    labels = PeriodSplit((date(2020, 1, 1), date(2024, 1, 1))).labels(days)
    assert labels.tolist() == ["2016〜2019", "2016〜2019", "2020〜2023", "2020〜2023", "2024〜2026", "2024〜2026"]


def test_理論の検証は同じ人気の馬とくらべた倍率を帯ごとに出す():
    theory = Theory("区分", "印つき", lambda t: t["flag"])
    table = TheoryCheckTable(min_runs=60, min_period_runs=20).build(_runners(), (theory,), title="t")
    rows = {row[1]: dict(zip(table.columns, row)) for row in table.rows}
    assert set(rows) == {ALL_BANDS, "大穴"}                      # 印は 9番人気だけなので、人気馬・中穴の行は出ない
    longshot = rows["大穴"]
    assert longshot["頭数"] == 100 and longshot["3着以内率"] == "100.0%"
    assert longshot["3着以内の倍率"] == 2.0                       # 9番人気の半分が来る中で、印つきは全部来る
    assert longshot["複勝回収率"] == "150.0%" and longshot["単勝回収率"] == "0.0%"
    assert longshot["倍率 2018〜2018"] == 2.0 and longshot["倍率 2025〜2025"] == 2.0


def test_頭数の足りない行は出さず_期間の頭数が足りない倍率は空():
    theory = Theory("区分", "印つき", lambda t: t["flag"])
    runners = _runners()
    assert TheoryCheckTable(min_runs=101).build(runners, (theory,), title="t").rows == []
    table = TheoryCheckTable(min_runs=60, min_period_runs=51).build(runners, (theory,), title="t")
    first = dict(zip(table.columns, table.rows[0]))
    assert first["倍率 2018〜2018"] is None and first["倍率 2025〜2025"] is None
