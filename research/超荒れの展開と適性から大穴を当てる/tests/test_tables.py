"""1行 = 1レースの表と、報告の表を、架空の出走の表で確かめる。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from 超荒れの展開と適性から大穴を当てる.analysis.case_sections import CaseSections
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.runner_enrichment import RunnerEnrichment, SideTables
from 超荒れの展開と適性から大穴を当てる.analysis.tables.case_selection import CaseSelection
from 超荒れの展開と適性から大穴を当てる.analysis.tables.concentration_table import ConcentrationTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.forecast_hit_table import ForecastHitTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.gap_table import GapTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.pair_alignment_table import PairAlignmentTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.pair_pattern_table import PairPatternTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.pre_close_table import PreCloseTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.upset_count_table import UpsetCountTable
from 超荒れの展開と適性から大穴を当てる.analysis.tables.win_shape_table import WinShapeTable
from 超荒れの展開と適性から大穴を当てる.analysis.theory.race_table import MULTI, OTHER, WIN_ONLY, RaceTable
from 超荒れの展開と適性から大穴を当てる.analysis.theory.runner_cuts import RunnerCuts

from .frames import LAST_RACE, history, side_tables


@pytest.fixture(scope="module")
def runners() -> pd.DataFrame:
    return RunnerCuts().add(RunnerEnrichment(date(2024, 1, 1)).build(history(), SideTables(**side_tables())))


@pytest.fixture(scope="module")
def races(runners: pd.DataFrame) -> pd.DataFrame:
    return RaceTable().build(runners)


def test_レースの表は大穴の来方で決着を分ける(races: pd.DataFrame):
    assert races.loc["2024010106010101", "outcome"] == OTHER
    assert races.loc["2024020106010101", "outcome"] == MULTI       # 10・11番人気が1・2着
    assert races.loc["2024030106010101", "outcome"] == OTHER
    assert races.loc[LAST_RACE, "outcome"] == MULTI
    assert bool(races.loc[LAST_RACE, "longshot_all"])
    assert races.loc[LAST_RACE, "favorite_finish"] == 4.0
    assert not races.loc[LAST_RACE, "pre_close_longshot_won"]      # 勝った10番人気は締め切り前は9番人気
    assert pd.isna(races.loc["2024020106010101", "pre_close_longshot_won"])
    assert races["longshot_market"].between(0, 1).all()


def test_数の表は切り口ごとと全レースの行を出す(races: pd.DataFrame):
    table = UpsetCountTable().build(races, "ハンデ戦か", "t")
    labels = [row[0] for row in table.rows]
    assert labels == ["ハンデ戦", "ハンデ戦以外", "（全レース）"]
    total = table.rows[-1]
    assert total[1] == 4 and total[2] == 2 and total[5] == 2 and total[7] == 1


def test_人気から見た差は実際の率と期待の率の差(runners: pd.DataFrame):
    table = GapTable().build(runners, ["人気"], "t", min_runs=1)
    rows = {row[0]: row for row in table.rows}
    assert rows["1番人気"][1] == 4
    assert rows["10番人気以下"][2] == "41.7%"                         # 12頭のうち5頭が3着以内（2月に2頭、4月に3頭）
    assert rows["10番人気以下"][3].startswith("+0.00")                # 全部の馬で数えた期待なので差は 0


def test_集まり方は大穴の中で市場の見立てとくらべる(runners: pd.DataFrame, races: pd.DataFrame):
    in_won = runners.loc[runners["longshot"] & runners["race_id"].isin(races.index[races["longshot_won"]])]
    table = ConcentrationTable("won").build(in_won, ["人気"], "t", min_runs=1)
    assert table.rows[0][1:4] == [6, 2, "2.0"]                       # 2レースの大穴6頭、勝ち2頭、市場から見た数も合計2
    multi = runners.loc[runners["longshot"] & runners["race_id"].isin(races.index[races["longshot_multi"]])]
    top3 = ConcentrationTable("top3").build(multi, ["人気"], "t", min_runs=1)
    assert top3.rows[0][2] == 5 and top3.rows[0][3] == "5.0"


def test_大穴の組の形と組み合わせ(runners: pd.DataFrame, races: pd.DataFrame):
    multi = races.index[races["longshot_multi"]]
    table = PairAlignmentTable().build(runners, multi, "t")
    side = next(row for row in table.rows if row[0] == "枠の側（内・中・外）")
    assert side[1] == 1 + 3                                          # 2月は1組、4月は3頭なので3組
    assert side[2] == "100.0%"                                       # 10〜12番は全部 外
    pattern = PairPatternTable().build(runners, races, "t")
    assert pattern.rows[-1][-1] == 1                                 # ペースの分かる大穴2頭以上のレースは4月だけ


def test_事例は決めた数を選び_ハンデ戦を先に選ぶ(races: pd.DataFrame):
    chosen = CaseSelection().pick(races, MULTI, 2, 1)
    assert len(chosen) == 2
    assert chosen[0] == LAST_RACE                                    # ハンデ戦（4月）が先
    assert CaseSelection().pick(races, WIN_ONLY, 5, 2) == []


def test_そのほかの表(runners: pd.DataFrame, races: pd.DataFrame):
    shape = WinShapeTable().build(runners.loc[runners["won"] > 0], "t")
    assert shape.rows[-1][-1] == 1                                   # ペースの分かる勝ち馬は4月の1頭
    hit = ForecastHitTable().summary(races, "t")
    assert hit.rows[0][1] == 1 and hit.rows[0][2] == "100.0%"
    pre = PreCloseTable().build(races, "t")
    assert pre.rows[0][1] == 1 and pre.rows[1][1] == 0


def test_報告の節は全部作れる(runners: pd.DataFrame, races: pd.DataFrame):
    sections = CaseSections(runners, races).build()
    assert [name for name, _ in sections][0] == "1. 事例の数"
    assert all(tables for _, tables in sections)
