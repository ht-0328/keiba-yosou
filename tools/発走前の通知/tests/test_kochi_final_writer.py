"""KochiFinalWriter（高知ファイナルのときだけ、買い目をファイルに書く）のテスト。DB はメモリの中の架空の表。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from 高知ファイナルの買い目.final_bet_file import FinalBetFile

from 発走前の通知.kochi_final_writer import KochiFinalWriter

FINAL = "2025020954010112"
OTHER = "2025020954010111"


class _NoModels:
    def load(self):
        raise FileNotFoundError("高知ファイナルのモデルがありません")

    def popularity_rates(self) -> dict[float, float]:
        return {}


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE TABLE ra (開催年 VARCHAR, 開催月日 VARCHAR, 競馬場コード VARCHAR, レース番号 VARCHAR, 競走名本題 VARCHAR, データ区分 VARCHAR, データ作成年月日 VARCHAR)")
    con.executemany("INSERT INTO ra VALUES ('2025', '0209', '54', ?, ?, '2', '20250208')", [("11", "一般"), ("12", "ファイナルレース")])
    return con


def _odds_db(path: Path) -> Path:
    """FINAL の単勝・複勝オッズの断面が1つ入った、架空の時系列オッズの DB。"""
    key = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
    values = ["2025", "0209", "54", "01", "01", "12"]
    con = duckdb.connect(str(path))
    for table, columns in (("o1", ("データ区分", "発表月日時分")), ("o1__単勝オッズ", ("発表月日時分", "馬番", "オッズ")),
                           ("o1__複勝オッズ", ("発表月日時分", "馬番", "最低オッズ", "最高オッズ"))):
        con.execute(f'CREATE TABLE "{table}" ({", ".join(f"{name} VARCHAR" for name in (*key, *columns))})')
    con.execute("INSERT INTO o1 VALUES (?, ?, ?, ?, ?, ?, '1', '02092040')", values)
    for horse in range(1, 11):
        con.execute('INSERT INTO "o1__単勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [*values, "02092040", f"{horse:02d}", f"{horse * 20:04d}"])
        con.execute('INSERT INTO "o1__複勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [*values, "02092040", f"{horse:02d}", "0011", "0015"])
    con.close()
    return path


def test_高知ファイナルでないレースは_ファイルを作らず_前のファイルも消す(tmp_path: Path) -> None:
    out = tmp_path / f"{OTHER}.高知ファイナル.json"
    out.write_text("{}", encoding="utf-8")
    assert KochiFinalWriter(store=_NoModels()).write(_con(), OTHER, out, None) is None
    assert not out.exists()


def test_高知ファイナルで断面が無ければ_理由つきのなしを書く(tmp_path: Path) -> None:
    out = tmp_path / f"{FINAL}.高知ファイナル.json"
    bets = KochiFinalWriter(store=_NoModels()).write(_con(), FINAL, out, tmp_path / "無い.duckdb")
    assert bets.empty and "断面がまだ無い" in bets.reason and FinalBetFile().read(out) == bets


def test_出せなかったときも失敗にせず_理由を書く(tmp_path: Path) -> None:
    out = tmp_path / f"{FINAL}.高知ファイナル.json"
    bets = KochiFinalWriter(store=_NoModels()).write(_con(), FINAL, out, _odds_db(tmp_path / "時系列オッズ.duckdb"))
    assert bets.empty and "FileNotFoundError" in bets.reason and FinalBetFile().read(out).reason == bets.reason
