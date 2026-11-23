"""BaneiRunsRepository（ばんえいの出走を元DB から読んで数に直す）のテスト。メモリ上の DuckDB に架空の行を入れる。"""

from __future__ import annotations

import duckdb
import pytest

from ばんえいの予想.banei_runs_repository import BaneiRunsRepository

_KEY = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_RA = ("データ区分", "データ作成年月日", *_KEY, "発走時刻", "競走名本題", "競走条件名称", "グレードコード", "競走種別コード", "重量種別コード",
       "本賞金_1", "天候コード", "芝馬場状態コード", "ダート馬場状態コード")
_SE = ("データ区分", "データ作成年月日", *_KEY, "枠番", "馬番", "血統登録番号", "馬名", "性別コード", "馬齢", "調教師コード", "騎手コード",
       "負担重量", "馬体重", "増減符号", "増減差", "異常区分コード", "確定着順", "走破タイム", "単勝オッズ", "単勝人気順")
_OLD = ("2026", "1116", "83", "16", "06", "01")
_RACE = ("2026", "1123", "83", "17", "03", "09")
_RID = "".join(_RACE)


def _table(con: duckdb.DuckDBPyConnection, name: str, columns: tuple[str, ...], rows: list[tuple]) -> None:
    con.execute(f"CREATE TABLE {name} ({', '.join(f'{column} VARCHAR' for column in columns)})")
    con.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' for _ in columns)})", rows)


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    _table(con, "ra", _RA, [
        ("7", "20261116", *_OLD, "1400", "", "Ｃ１", "", "04", "8", "00003000", "1", "1", "C"),
        ("2", "20261122", *_RACE, "1830", "テスト", "Ｂ３－３", "", "04", "8", "00003400", "0", "0", "0"),
    ])
    _table(con, "se", _SE, [
        ("7", "20261116", *_OLD, "1", "01", "H1", "ウマイチ  ", "1", "05", "T1", "J1", "276", "39A", "-", "006", "0", "02", "2187", "0103", "06"),
        ("2", "20261122", *_RACE, "1", "01", "H1", "ウマイチ", "1", "05", "T1", "J1", "280", "", "", "", "0", "00", "0000", "0000", "00"),
        ("2", "20261122", *_RACE, "2", "02", "H2", "ウマニ", "2", "04", "T2", "J2", "276", "", "", "", "0", "00", "0000", "0000", "00"),
        ("2", "20261122", *_RACE, "3", "03", "H3", "ウマサン", "1", "06", "T3", "J3", "276", "", "", "", "0", "00", "0000", "0000", "00"),
    ])
    _table(con, "av", (*_KEY, "馬番"), [(*_RACE, "03")])
    _table(con, "jc", (*_KEY, "発表月日時分", "馬番", "騎手コード"), [(*_RACE, "11221256", "02", "J9")])
    _table(con, '"wh__馬体重情報"', (*_KEY, "_連番", "馬番", "馬体重", "増減符号", "増減差"), [(*_RACE, "1", "01", "3A0", "+", "006")])
    _table(con, "we", ("データ作成年月日", *_KEY[:3], "発表月日時分", "天候状態", '"馬場状態・芝"', '"馬場状態・ダート"'), [
        ("20261123", "2026", "1123", "83", "00000000", "1", "1", "9"),
        ("20261123", "2026", "1123", "83", "11231556", "0", "1", "8"),
    ])
    return con


def test_確定した出走は_16進の重さと水分とタイムを数に直す() -> None:
    row = BaneiRunsRepository(_db()).confirmed().iloc[0]
    assert (row["load"], row["bw"], row["bw_change"]) == (630, 922, -6)
    assert row["water"] == pytest.approx(2.8)
    assert row["time"] == pytest.approx(138.7)
    assert (row["finish"], row["win_odds"], row["pop"], row["name"]) == (2, 10.3, 6, "ウマイチ")


def test_予想するレースは_確定した出走に入れない() -> None:
    con = _db()
    con.execute("UPDATE ra SET データ区分 = '7'")
    con.execute("UPDATE se SET データ区分 = '7'")
    assert set(BaneiRunsRepository(con).confirmed(exclude_rid=_RID)["rid"]) == {"".join(_OLD)}


def test_出馬表は_取消を除き_騎手変更と馬体重と馬場水分の速報を重ねる() -> None:
    card = BaneiRunsRepository(_db()).card(_RID)
    assert card["umaban"].tolist() == [1, 2]
    assert card["jockey"].tolist() == ["J1", "J9"]
    assert card["bw"].iloc[0] == 928 and card["bw_change"].iloc[0] == 6
    assert card["bw"].isna().iloc[1]
    assert card["water"].tolist() == pytest.approx([2.4, 2.4])
    assert card["weather"].tolist() == [1, 1]
    assert card["finish"].isna().all() and card["win_odds"].isna().all()


def test_速報の表がまだ無くても_出馬表は読める() -> None:
    con = _db()
    for table in ("av", "jc", "we", '"wh__馬体重情報"'):
        con.execute(f"DROP TABLE {table}")
    card = BaneiRunsRepository(con).card(_RID)
    assert card["umaban"].tolist() == [1, 2, 3]
    assert card["water"].isna().all()


def test_出馬表が無ければ_LookupError() -> None:
    with pytest.raises(LookupError):
        BaneiRunsRepository(_db()).card("2026112383170312")
