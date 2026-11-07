"""PastStyleRepository（出走馬の、そのレースより前の走の脚質の材料）のテスト。メモリ上の DuckDB に架空の se・ra・コーナー通過順位を入れる。"""

from __future__ import annotations

import duckdb

from 発走前の通知.past_style_repository import PastStyleRepository

_KEYS = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_SE = ("データ区分", "データ作成年月日", *_KEYS, "馬番", "血統登録番号", "今回レース脚質判定",
       '"1コーナーでの順位"', '"2コーナーでの順位"', '"3コーナーでの順位"', '"4コーナーでの順位"')
_RA = ("データ区分", "データ作成年月日", *_KEYS, "出走頭数")
_CORNERS = (*_KEYS, '"_連番"', "コーナー", "周回数", "各通過順位")


def _keys(day: str, venue: str, race_no: str) -> list[str]:
    return [day[:4], day[4:], venue, "05", "02", race_no]


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for table, columns in (("se", _SE), ("ra", _RA), ("ra__コーナー通過順位", _CORNERS)):
        con.execute(f"CREATE TABLE {table} ({', '.join(f'{name} VARCHAR' for name in columns)})")

    def se(day: str, venue: str, race_no: str, horse_no: str, horse_id: str, style: str, corners: tuple[str, str, str, str],
           kubun: str = "7") -> None:
        con.execute(f"INSERT INTO se VALUES ({', '.join('?' for _ in _SE)})",
                    [kubun, day, *_keys(day, venue, race_no), horse_no, horse_id, style, *corners])

    def ra(day: str, venue: str, race_no: str, field: str) -> None:
        con.execute(f"INSERT INTO ra VALUES ({', '.join('?' for _ in _RA)})", ["7", day, *_keys(day, venue, race_no), field])

    def corner(day: str, venue: str, race_no: str, seq: str, number: str, lap: str) -> None:
        con.execute(f"INSERT INTO ra__コーナー通過順位 VALUES ({', '.join('?' for _ in _CORNERS)})",
                    [*_keys(day, venue, race_no), seq, number, lap, "1,2,3"])

    se("20261108", "05", "11", "03", "A", "", ("00", "00", "00", "00"))           # 今回のレース
    se("20261101", "05", "05", "07", "A", "2", ("00", "00", "04", "03"))          # 前の走（3コーナーから記録）
    se("20261101", "05", "05", "07", "A", "3", ("00", "00", "06", "05"), "6")     # 同じ走の古い行（読まない）
    ra("20261101", "05", "05", "12")
    corner("20261101", "05", "05", "1", "3", "1")
    corner("20261101", "05", "05", "2", "4", "1")
    se("20261018", "05", "02", "01", "A", "", ("02", "03", "04", "05"))           # 2周するレース → 4コーナー
    ra("20261018", "05", "02", "10")
    corner("20261018", "05", "02", "1", "3", "1")
    corner("20261018", "05", "02", "2", "1", "2")
    se("20261010", "45", "01", "01", "A", "1", ("01", "01", "01", "01"))          # ほかの組織の競馬場（読まない）
    se("20261108", "05", "11", "05", "B", "", ("00", "00", "00", "00"))           # 過去走の無い馬
    return con


def test_出走馬の前の走を新しい順に_最初のコーナーの順位と頭数つきで読む() -> None:
    past = PastStyleRepository(_db()).read("2026110805050211")
    assert past["horse_no"].tolist() == [3, 3]
    assert past["race_day"].tolist() == ["20261101", "20261018"]
    assert past["style_code"].tolist() == ["2", ""]
    assert past["corner"].tolist() == [4, 5]   # 最初に記録された3コーナーの順位、2周するレースは4コーナー
    assert past["field_size"].tolist() == [12, 10]
