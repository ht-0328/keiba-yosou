"""締め切り前の断面の選び方と、締め切り前のオッズでの材料の作り直しのテスト。架空の値だけを使う。"""

from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import pandas as pd
import pytest

from 回収率100超.analysis.feature import LearningTable, PreDeadlineTable
from 回収率100超.analysis.market import SternProbabilities
from 回収率100超.analysis.repository import PreDeadlineQuinellaRepository, PreDeadlineWinPlaceRepository

KEYS = ("開催年", "開催月日", "競馬場コード", "開催回[第N回]", "開催日目[N日目]", "レース番号")
RACE = ("2026", "0906", "06", "04", "02", "11")
RID = "".join(RACE)
DAY = date(2026, 9, 6)


def _create(con, table: str, columns: tuple[str, ...]) -> None:
    con.execute(f'CREATE TABLE "{table}" ({", ".join(f"{chr(34)}{c}{chr(34)} VARCHAR" for c in columns)})')


def _insert(con, table: str, values: list[str]) -> None:
    con.execute(f'INSERT INTO "{table}" VALUES ({", ".join("?" for _ in values)})', values)


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    """発走 15:40 のレース。単複枠と馬連の断面が、前日・発走30分前・12分前・8分前・最終・確定にある。"""
    con = duckdb.connect()
    _create(con, "ra", (*KEYS, "データ区分", "データ作成年月日", "発走時刻"))
    _insert(con, "ra", [*RACE, "7", "20260906", "1540"])
    for table in ("o1", "o2"):
        _create(con, table, (*KEYS, "データ区分", "発表月日時分"))
    _create(con, "o1__単勝オッズ", (*KEYS, "発表月日時分", "馬番", "オッズ"))
    _create(con, "o1__複勝オッズ", (*KEYS, "発表月日時分", "馬番", "最低オッズ", "最高オッズ"))
    _create(con, "o2__馬連オッズ", (*KEYS, "発表月日時分", "組番", "オッズ"))
    snapshots = [("2", "09051733", "0100"), ("1", "09061510", "0200"), ("1", "09061528", "0300"),
                 ("1", "09061532", "0400"), ("3", "09061540", "0500"), ("4", "09061548", "0600")]
    for stage, announced, odds in snapshots:
        for table in ("o1", "o2"):
            _insert(con, table, [*RACE, stage, announced])
        _insert(con, "o1__単勝オッズ", [*RACE, announced, "01", odds])
        _insert(con, "o1__単勝オッズ", [*RACE, announced, "02", "0020"])
        _insert(con, "o1__複勝オッズ", [*RACE, announced, "01", odds, odds])
        _insert(con, "o2__馬連オッズ", [*RACE, announced, "0102", odds])
        _insert(con, "o2__馬連オッズ", [*RACE, announced, "0203", "0100"])
    return con


def test_発走10分前までの_いちばん新しい締め切り前の断面を使う(con) -> None:
    frame = PreDeadlineWinPlaceRepository(con, DAY, DAY, 10).read().set_index("horse_no")
    assert frame.loc[1, "announced"] == "09061528", "8分前の断面・最終・確定は、10分前の時点ではまだ見えない"
    assert frame.loc[1, "win_odds"] == pytest.approx(30.0) and frame.loc[1, "place_odds_low"] == pytest.approx(30.0)


def test_何分前かを変えると使う断面が変わる(con) -> None:
    frame = PreDeadlineWinPlaceRepository(con, DAY, DAY, 20).read().set_index("horse_no")
    assert frame.loc[1, "announced"] == "09061510"


def test_馬連の断面から馬ごとの2着以内の確率を作る(con) -> None:
    frame = PreDeadlineQuinellaRepository(con, DAY, DAY, 10).read().set_index("horse_no")
    # 12分前の断面: 組 1-2 が 30倍、組 2-3 が 10倍。合計を 1 にそろえると 0.25 と 0.75。
    assert frame.loc[1, "馬連から見た2着以内率"] == pytest.approx(0.25)
    assert frame.loc[2, "馬連から見た2着以内率"] == pytest.approx(1.0)


def test_期間の外のレースは読まない(con) -> None:
    assert PreDeadlineWinPlaceRepository(con, date(2026, 9, 7), date(2026, 9, 8), 10).read().empty


def _rows() -> pd.DataFrame:
    """確定オッズで作った学習の表の一部（2レース × 5頭）。"""
    rows = pd.DataFrame({"rid": ["R1"] * 5 + ["R2"] * 5, "horse_no": list(range(1, 6)) * 2,
                         "place_places": 2, "win_odds": 5.0, "place_odds_low": 1.5, "place_odds_high": 2.0,
                         "馬連から見た2着以内率": 0.4, "複勝から見た3着以内率": 0.4, "単勝から見た勝率": 0.2})
    return rows


def _pre(rid_missing: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = _rows()
    win_place = rows[["rid", "horse_no"]].assign(win_odds=np.tile([2.0, 4.0, 8.0, 16.0, 32.0], 2),
                                                 place_odds_low=1.2, place_odds_high=1.6)
    if rid_missing:
        win_place = win_place[~((win_place["rid"] == rid_missing) & (win_place["horse_no"] == 5))]
    quinella = rows[["rid", "horse_no"]].assign(馬連から見た2着以内率=0.4)
    return win_place, quinella


def test_締め切り前の単勝オッズで勝率と複勝率を作り直す() -> None:
    table = PreDeadlineTable(LearningTable(SternProbabilities(1.0, 1.0)))
    frame = table.rebuild(_rows(), *_pre()).set_index(["rid", "horse_no"])
    inverse = np.array([1 / 2, 1 / 4, 1 / 8, 1 / 16, 1 / 32])
    assert frame.loc[("R1", 1), "単勝から見た勝率"] == pytest.approx(inverse[0] / inverse.sum())
    assert frame.loc["R1", "単勝から見た複勝率"].sum() == pytest.approx(2.0), "5頭立ては2着まで"
    assert frame.loc[("R1", 1), "log_単勝から見た勝率"] == pytest.approx(np.log(inverse[0] / inverse.sum()))


def test_締め切り前の値が1頭でも欠けるレースは落とす() -> None:
    table = PreDeadlineTable(LearningTable(SternProbabilities(1.0, 1.0)))
    frame = table.rebuild(_rows(), *_pre(rid_missing="R2"))
    assert set(frame["rid"]) == {"R1"}


def test_締め切り前に手に入らないプールの列を外す() -> None:
    table = PreDeadlineTable(LearningTable(SternProbabilities(1.0, 1.0)))
    features = ["log_3連単から見た勝率", "3連複から見た3着以内率と単勝の差", "順位_単勝票数の配分",
                "log_馬連から見た2着以内率", "複勝から見た3着以内率と単勝の差", "log_単勝から見た勝率", "age"]
    assert table.features(features) == ["log_馬連から見た2着以内率", "複勝から見た3着以内率と単勝の差",
                                        "log_単勝から見た勝率", "age"]
