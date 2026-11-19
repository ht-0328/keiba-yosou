"""通知のときの推奨買目の作り直しと、期待の儲けの高低ごとの成績の表を、架空の値で確かめる（実DB は使わない）。"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

from 地方の期待度.analysis.late_snapshot_repository import LateSnapshotRepository
from 地方の期待度.analysis.notified_bets import NotifiedBets
from 地方の期待度.analysis.notified_grade_table import NotifiedGradeTable
from 地方の期待度.analysis.notified_payout_repository import NotifiedPayoutRepository

_A, _B, _C = "2026110944120101", "2026110944120102", "2026110844120101"
_KEYS = '"開催年" VARCHAR, "開催月日" VARCHAR, "競馬場コード" VARCHAR, "開催回[第N回]" VARCHAR, "開催日目[N日目]" VARCHAR, "レース番号" VARCHAR'


class _Recommender:
    def recommend(self, rid: str, forecast: dict) -> RecommendationSet:
        if rid == _B:
            raise LookupError("3連単のオッズがまだ DB にありません")
        return RecommendationSet((Recommendation("単勝", (3,), 5.0, 0.3, 1.5), Recommendation("馬単", (3, 7), 20.0, 0.06, 1.2)))


def _save(folder: Path, rid: str, timing: str = "当日") -> None:
    day = folder / f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}"
    day.mkdir(parents=True, exist_ok=True)
    (day / f"{rid}.json").write_text(json.dumps({"title": f"{rid} の予測: {timing}の時点", "columns": [], "rows": []}, ensure_ascii=False), encoding="utf-8")
    (day / f"{rid}.荒れ具合.json").write_text("{}", encoding="utf-8")   # 予想のファイルではないので読まない


def test_保存した当日の予想だけから_1点1行の表を作る(tmp_path: Path) -> None:
    _save(tmp_path, _A)
    _save(tmp_path, _B)                       # 推奨買目を出せなかったレースは数えない
    _save(tmp_path, _C)                       # 対象の日より前
    _save(tmp_path, "2026110944120103", "前日")
    _save(tmp_path, "2026110944120104")       # 締め切り後の断面があるレース
    bets = NotifiedBets(_Recommender(), tmp_path, frozenset({"2026110944120104"})).build("2026-11-09")
    assert bets["race_id"].tolist() == [_A, _A] and bets["ticket"].tolist() == ["単勝", "馬単"]
    assert bets["numbers"].tolist() == [(3,), (3, 7)] and bets["ev"].tolist() == [1.5, 1.2] and set(bets["race_date"]) == {"2026-11-09"}


def test_払戻は組番を番号の組にして読む_枠連は1桁ずつ() -> None:
    con = duckdb.connect()
    for table, column in (("hr__馬単払戻", "組番"), ("hr__枠連払戻", "組番"), ("hr__単勝払戻", "馬番")):
        con.execute(f'CREATE TABLE "{table}" ({_KEYS}, "{column}" VARCHAR, "払戻金" VARCHAR)')
    con.execute("""INSERT INTO "hr__馬単払戻" VALUES ('2026','1109','44','12','01','01','0307','000002310'), ('2026','1108','44','12','01','01','0102','000000500'),
                   ('2026','1109','44','12','01','02','    ','000000000')""")
    con.execute("""INSERT INTO "hr__枠連払戻" VALUES ('2026','1109','44','12','01','01','38','000000640')""")
    con.execute("""INSERT INTO "hr__単勝払戻" VALUES ('2026','1109','44','12','01','01','03','000000450')""")
    repository = NotifiedPayoutRepository(con)
    exacta = repository.load("馬単", "20261109", "99991231")
    assert exacta[["race_id", "numbers", "payout"]].values.tolist() == [[_A, (3, 7), 2310]]
    assert repository.load("枠連", "20261109", "99991231")["numbers"].tolist() == [(3, 8)]
    assert repository.load("単勝", "20261109", "99991231")["numbers"].tolist() == [(3,)]


def test_締め切り後の断面のあるレースだけを返す() -> None:
    con = duckdb.connect()
    con.execute(f'CREATE TABLE o6 ({_KEYS}, "データ区分" VARCHAR, "発表月日時分" VARCHAR)')
    con.execute("""INSERT INTO o6 VALUES ('2026','1109','44','12','01','01','1','11091015'), ('2026','1109','44','12','01','01','5','00000000'),
                   ('2026','1109','44','12','01','02','1','11091045'), ('2026','1109','44','12','01','02','4','11091101'),
                   ('2026','1108','44','12','01','01','3','11081030')""")
    assert LateSnapshotRepository(con).load("20261109") == frozenset({_B})


def test_表は_等級と点数の高低の組ごとに_回収率と儲けを並べる() -> None:
    rows = []
    for index, (value, payout) in enumerate([(1.1, 300), (1.2, 0), (2.0, 0), (3.0, 0), (5.5, 0)]):
        rid = f"20261109441201{index + 1:02d}"
        rows += [(rid, "2026-11-09", "単勝", (1,), 5.0, value, payout), (rid, "2026-11-09", "複勝", (2,), 2.0, 1.0, 0)]
    bets = pd.DataFrame(rows, columns=["race_id", "race_date", "ticket", "numbers", "odds", "ev", "payout"])
    table = NotifiedGradeTable().table(bets, "題")
    assert table.rows[0] == ["全体", "全体", 5, "100.0%", "2.0", "30.0%", "20.0%", "-140"]
    by_grade = {row[1]: row for row in table.rows if row[0] == "期待の儲けの等級"}
    assert by_grade["S"][2:4] == [1, "20.0%"] and by_grade["A"][2] == 1 and by_grade["B"][2] == 1 and by_grade["C"][2] == 2
    assert by_grade["C"][5] == "75.0%" and by_grade["S"][5] == "0.0%"
    bands = [row for row in table.rows if row[0] == "点数の低い順の組"]
    assert len(bands) == 5 and bands[0][1] == "1（0.10〜0.10）" and bands[0][5] == "150.0%" and bands[-1][1] == "5（4.50〜4.50）"
