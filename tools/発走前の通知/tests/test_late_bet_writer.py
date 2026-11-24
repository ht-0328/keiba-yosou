"""LateBetWriter（発走前の予想と同じ接続で、直前の買い目をファイルに書く）のテスト。モデルと予想の確率は偽物、時系列オッズは架空の行。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.feature import PredictionTiming

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_bet_file import LateBetFile
from 地方の直前の買い目.testing.fake_models import FakeModels

from 発走前の通知.late_bet_writer import LateBetWriter

RID = "2026111844120105"
_KEY = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_KEY_VALUES = ("2026", "1118", "44", "12", "01", "05")
HEADS = 7


class _Store:
    def __init__(self, models: FakeModels | None) -> None:
        self._models = models

    def load(self) -> FakeModels:
        if self._models is None:
            raise FileNotFoundError("直前の買い目のモデルがありません")
        return self._models


class _Probabilities:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def of(self, con, rid: str, db_path) -> pd.DataFrame:
        self.calls.append(rid)
        numbers = list(range(1, HEADS + 1))
        return pd.DataFrame({c.HORSE_NO: numbers, c.WIN_MODEL: [1 / HEADS] * HEADS, c.TOP3_MODEL: [3 / HEADS] * HEADS,
                             c.WIN_FREE: [1 / HEADS] * HEADS, c.TOP3_FREE: [3 / HEADS] * HEADS})


def _odds_db(path: Path) -> Path:
    con = duckdb.connect(str(path))
    for table, columns in (("o1", ("データ区分", "発表月日時分")), ("o1__単勝オッズ", ("発表月日時分", "馬番", "オッズ")),
                           ("o1__複勝オッズ", ("発表月日時分", "馬番", "最低オッズ", "最高オッズ"))):
        con.execute(f'CREATE TABLE "{table}" ({", ".join(f"{name} VARCHAR" for name in (*_KEY, *columns))})')
    con.execute("INSERT INTO o1 VALUES (?, ?, ?, ?, ?, ?, '1', '11181530')", list(_KEY_VALUES))
    for horse in range(1, HEADS + 1):
        con.execute('INSERT INTO "o1__単勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [*_KEY_VALUES, "11181530", f"{horse:02d}", f"{horse * 20:04d}"])
        con.execute('INSERT INTO "o1__複勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [*_KEY_VALUES, "11181530", f"{horse:02d}", "0011", "0015"])
    con.close()
    return path


def _writer(models: FakeModels | None, probabilities: _Probabilities | None = None) -> LateBetWriter:
    return LateBetWriter(store=_Store(models), probabilities=probabilities or _Probabilities())


def test_当日の時点は_時系列オッズと予想の確率から買う馬を決めて書く(tmp_path: Path) -> None:
    out = tmp_path / "日" / f"{RID}.直前.json"
    bets = _writer(FakeModels({6: 0.5}, {6: 1.2})).write(None, RID, out, _odds_db(tmp_path / "ts.duckdb"), None, PredictionTiming.RACE_DAY)
    assert [pick.horse_no for pick in bets.picks] == [6] and bets.picks[0].odds == 12.0
    assert LateBetFile().read(out) == replace(bets, closeness=round(bets.closeness, 4)) and bets.announced == "11181530"   # 線への近さは小数4桁で書く


def test_前日の時点は出さず_予想の確率も出さない(tmp_path: Path) -> None:
    probabilities = _Probabilities()
    out = tmp_path / f"{RID}.直前.json"
    bets = _writer(FakeModels({6: 0.5}, {6: 1.2}), probabilities).write(None, RID, out, _odds_db(tmp_path / "ts.duckdb"), None,
                                                                         PredictionTiming.DAY_BEFORE)
    assert bets.empty and "前日の時点では出さない" in bets.reason and probabilities.calls == []
    assert LateBetFile().read(out) == bets


def test_時系列オッズのファイルが無ければ_理由つきのなし(tmp_path: Path) -> None:
    out = tmp_path / f"{RID}.直前.json"
    bets = _writer(FakeModels({6: 0.5}, {6: 1.2})).write(None, RID, out, tmp_path / "無い.duckdb", None, PredictionTiming.RACE_DAY)
    assert bets.empty and "断面がまだ無い" in bets.reason


def test_失敗しても止めず_理由を書き_前の買い目は残さない(tmp_path: Path) -> None:
    out = tmp_path / f"{RID}.直前.json"
    odds = _odds_db(tmp_path / "ts.duckdb")
    _writer(FakeModels({6: 0.5}, {6: 1.2})).write(None, RID, out, odds, None, PredictionTiming.RACE_DAY)
    bets = _writer(None).write(None, RID, out, odds, None, PredictionTiming.RACE_DAY)
    assert bets.empty and bets.reason.startswith("FileNotFoundError") and LateBetFile().read(out) == bets
