"""Recommender（1レースの推奨買目の流れ）のテスト。メモリ上の DuckDB に架空の 11頭のオッズを入れ、係数 0（どの組も同じ確率）で、
期待値がオッズだけで決まることを使って選ばれる組を確かめる。"""

from __future__ import annotations

from itertools import combinations, permutations

import duckdb
import pytest

from 地方の推奨買目.position_coefficients import PositionCoefficients
from 地方の推奨買目.position_features import FIRST_FEATURES, SECOND_FEATURES, THIRD_FEATURES
from 地方の推奨買目.recommender import Recommender
from 地方の推奨買目.ticket_plan import TicketPlan

RID = "2026110550170505"
_KEY = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_KEY_VALUES = ("2026", "1105", "50", "17", "05", "05")
_AT = "11051225"
N = 11
COLUMNS = ["馬番", "馬名", "単勝オッズ", "1着になる確率", "1着になる確率（LightGBM）", "1着になる確率（CatBoost）", "3着以内に入る確率", "LightGBM", "CatBoost"]


def _forecast(heads: int = N) -> dict:
    rows = [[no, f"ウマ{no}", 5.0 + no, 0.1, 0.1, 0.1, 0.3, 0.3, 0.3] for no in range(1, heads + 1)]
    return {"columns": COLUMNS, "rows": rows}


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    key_sql = ", ".join(f"{name} VARCHAR" for name in _KEY)
    for head in ("o1", "o2", "o3", "o4", "o5", "o6"):
        con.execute(f"CREATE TABLE {head} (データ区分 VARCHAR, {key_sql}, 発表月日時分 VARCHAR)")
        con.execute(f"INSERT INTO {head} VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("1", *_KEY_VALUES, _AT))
    con.execute(f'CREATE TABLE "o1__単勝オッズ" ({key_sql}, 発表月日時分 VARCHAR, 馬番 VARCHAR, オッズ VARCHAR)')
    con.executemany('INSERT INTO "o1__単勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    [(*_KEY_VALUES, _AT, f"{no:02d}", f"{(5 + no) * 10:04d}") for no in range(1, N + 1)])   # 6.0〜16.0倍
    con.execute(f'CREATE TABLE "o1__複勝オッズ" ({key_sql}, 発表月日時分 VARCHAR, 馬番 VARCHAR, 最低オッズ VARCHAR, 最高オッズ VARCHAR)')
    con.executemany('INSERT INTO "o1__複勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    [(*_KEY_VALUES, _AT, f"{no:02d}", "0020", "0030") for no in range(1, N + 1)])      # 幅の真ん中 2.5倍
    con.execute(f'CREATE TABLE "o1__枠連オッズ" ({key_sql}, 発表月日時分 VARCHAR, 組番 VARCHAR, オッズ VARCHAR)')
    con.executemany('INSERT INTO "o1__枠連オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    [(*_KEY_VALUES, _AT, f"{a}{b}", "0200") for a, b in combinations(range(1, 9), 2)] + [(*_KEY_VALUES, _AT, f"{a}{a}", "0200") for a in (6, 7, 8)])   # 20倍
    for table, pairs in (('"o2__馬連オッズ"', combinations(range(1, N + 1), 2)), ('"o4__馬単オッズ"', permutations(range(1, N + 1), 2))):
        con.execute(f"CREATE TABLE {table} ({key_sql}, 発表月日時分 VARCHAR, 組番 VARCHAR, オッズ VARCHAR)")
        con.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [(*_KEY_VALUES, _AT, f"{a:02d}{b:02d}", "1000") for a, b in pairs])
    con.execute(f'CREATE TABLE "o3__ワイドオッズ" ({key_sql}, 発表月日時分 VARCHAR, 組番 VARCHAR, 最低オッズ VARCHAR, 最高オッズ VARCHAR)')
    con.executemany('INSERT INTO "o3__ワイドオッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    [(*_KEY_VALUES, _AT, f"{a:02d}{b:02d}", "0100", "0200") for a, b in combinations(range(1, N + 1), 2)])
    con.execute(f'CREATE TABLE "o5__3連複オッズ" ({key_sql}, 発表月日時分 VARCHAR, 組番 VARCHAR, オッズ VARCHAR)')
    con.executemany('INSERT INTO "o5__3連複オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    [(*_KEY_VALUES, _AT, f"{a:02d}{b:02d}{c:02d}", "3000") for a, b, c in combinations(range(1, N + 1), 3)])
    con.execute(f'CREATE TABLE "o6__3連単オッズ" ({key_sql}, 発表月日時分 VARCHAR, 組番 VARCHAR, オッズ VARCHAR)')
    con.executemany('INSERT INTO "o6__3連単オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    [(*_KEY_VALUES, _AT, f"{a:02d}{b:02d}{c:02d}", "15000" if (a, b, c) == (1, 2, 3) else "9000") for a, b, c in permutations(range(1, N + 1), 3)])
    con.execute(f"CREATE TABLE se (データ区分 VARCHAR, データ作成年月日 VARCHAR, {key_sql}, 枠番 VARCHAR, 馬番 VARCHAR)")
    frames = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 6, 8: 7, 9: 7, 10: 8, 11: 8}
    con.executemany("INSERT INTO se VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [("7", "20261105", *_KEY_VALUES, str(frame), f"{no:02d}") for no, frame in frames.items()])
    return con


def _zero() -> PositionCoefficients:
    return PositionCoefficients(dict.fromkeys(FIRST_FEATURES, 0.0), dict.fromkeys(SECOND_FEATURES, 0.0), dict.fromkeys(THIRD_FEATURES, 0.0))


def test_係数0なら組の確率は等しく_期待値はオッズで決まる():
    # 単勝 P = 1/11 なので、期待値 1 以上は 11倍以上（馬番 6〜11）。30倍以下の帯なので全部残る
    chosen = Recommender(_db(), _zero(), plans=(TicketPlan("単勝", 1.0, 0.0, 30.0), TicketPlan("3連単", 1.05, 10.0, 200.0))).recommend(RID, _forecast())
    assert [row.label for row in chosen.rows if row.ticket == "単勝"] == ["6", "7", "8", "9", "10", "11"]
    win = next(row for row in chosen.rows if row.ticket == "単勝" and row.numbers == (11,))
    assert win.odds == pytest.approx(16.0) and win.probability == pytest.approx(1 / 11) and win.value == pytest.approx(16 / 11)
    # 3連単 P = 1/990。1500倍の組だけ 期待値 1.5 だが 200倍の帯の外、900倍も外 → 3連単は無し
    assert not any(row.ticket == "3連単" for row in chosen.rows)
    assert chosen.points == 6 and chosen.yen == 600


def test_枠連は枠に写した確率で選ぶ():
    # 枠連の組の確率は、その2つの枠の馬の馬連（各 1/55）の和。20倍のオッズなので 確率 0.05 以上 = 馬が2頭ずつの枠どうし（4/55）だけ
    chosen = Recommender(_db(), _zero(), plans=(TicketPlan("枠連", 1.0),)).recommend(RID, _forecast())
    assert all(row.ticket == "枠連" for row in chosen.rows)
    assert all(row.probability * row.odds >= 1.0 for row in chosen.rows)
    assert [row.label for row in chosen.rows] == ["6-7", "6-8", "7-8"]
    assert chosen.rows[0].probability == pytest.approx(4 / 55) and chosen.rows[0].odds == pytest.approx(20.0)


def test_頭数の線は券種ごとに_届かない券種は出さず理由に添える():
    plans = (TicketPlan("単勝", 1.0, 0.0, 30.0), TicketPlan("3連単", 1.05, 10.0, 200.0, min_heads=11), TicketPlan("馬単", 1.05, 0.0, 50.0, min_heads=11))
    chosen = Recommender(_db(), _zero(), plans=plans).recommend(RID, _forecast(heads=10))
    assert {row.ticket for row in chosen.rows} == {"単勝"}
    assert chosen.reason == "10頭なので 3連単・馬単 は推奨買目の対象外"


def test_どの券種も頭数に届かなければ_計算せずに対象外():
    chosen = Recommender(_db(), _zero(), plans=(TicketPlan("3連単", 1.05, 10.0, 200.0, min_heads=11),)).recommend(RID, _forecast(heads=9))
    assert chosen.none and chosen.reason == "9頭なので 3連単 は推奨買目の対象外"
