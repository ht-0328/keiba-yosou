"""回顧の3つの表を、keiba-yosou が書き込める DuckDB のファイルに書く・読む。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from . import names

#: keiba-yosou のリポジトリ直下（src/yosou/review/ から3つ上）と、置き場所の既定（Git の対象外の reports/回顧/）。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REVIEW_DB = _PROJECT_ROOT / "reports" / "回顧" / "review.duckdb"

#: 表ごとの列と型（DuckDB の CREATE TABLE）。鍵の列は先頭。
_SCHEMAS: dict[str, tuple[tuple[str, str], ...]] = {
    names.BETS_TABLE: (
        (names.RACE_ID, "VARCHAR"), (names.TICKET_TYPE, "VARCHAR"), (names.COMBO, "VARCHAR"), (names.RACE_DATE, "DATE"),
        (names.PARTICIPATION, "VARCHAR"), (names.RECORD_ONLY, "BOOLEAN"), (names.STAKE_YEN, "INTEGER"), (names.BOUGHT_PROBABILITY, "DOUBLE"),
        (names.BOUGHT_VALUE, "DOUBLE"), (names.BOUGHT_ODDS, "DOUBLE"), (names.ODDS_AT, "VARCHAR"), (names.PAYOUT_YEN, "INTEGER"), (names.SETTLED, "BOOLEAN"),
    ),
    names.RACES_TABLE: (
        (names.RACE_ID, "VARCHAR"), (names.RACE_DATE, "DATE"), (names.FORECAST_PACE, "VARCHAR"), (names.FORECAST_HIGH, "DOUBLE"),
        (names.FORECAST_SLOW, "DOUBLE"), (names.RESULT_PACE, "VARCHAR"), (names.DAY_INNER_SLOPE, "DOUBLE"), (names.DAY_FRONT_SLOPE, "DOUBLE"),
        (names.CONDITION, "VARCHAR"),
    ),
    names.HORSES_TABLE: (
        (names.RACE_ID, "VARCHAR"), (names.HORSE_ID, "VARCHAR"), (names.RACE_DATE, "DATE"), (names.HANDICAPS, "VARCHAR"), (names.DEGREE, "INTEGER"),
        (names.NEXT_RUN, "VARCHAR"), (names.LATE_START_DEGREE, "INTEGER"), (names.PACE_DEGREE, "INTEGER"), (names.BIAS_DEGREE, "INTEGER"),
        (names.LATE_START_GAP, "DOUBLE"), (names.RESULT_SCORE, "DOUBLE"), (names.RESULT_BIAS, "DOUBLE"),
    ),
    names.COVERAGE_TABLE: ((names.AS_OF, "DATE"),),
}
#: 表ごとの鍵（同じ鍵の行は置き換える）。
_KEYS: dict[str, tuple[str, ...]] = {
    names.BETS_TABLE: (names.RACE_ID, names.TICKET_TYPE, names.COMBO), names.RACES_TABLE: (names.RACE_ID,),
    names.HORSES_TABLE: (names.RACE_ID, names.HORSE_ID),
}


class ReviewStore:
    """``reports/回顧/review.duckdb`` に、表1「買い目の記録」・表2「レースの回顧」・表3「馬の回顧ノート」と、表3を書いた範囲
    （最後の開催日）を持つ。同じ鍵の行は置き換える（レースのあとに払戻を書き足すなど）。jvdata-store の元DB とは別のファイル。

    馬名・オッズ・払戻が入るので Git の対象外に置く。NotebookLM には上げない（利用者の決定）。
    """

    def __init__(self, path: Path = DEFAULT_REVIEW_DB) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, table: str, rows: pd.DataFrame) -> int:
        """``rows`` を表に入れる（同じ鍵の行は置き換える）。入れた行の数を返す。"""
        columns = [column for column, _ in _SCHEMAS[table]]
        frame = rows.reindex(columns=columns)
        if frame.empty:
            return 0
        keys = list(_KEYS.get(table, ()))
        with self._open() as con:
            con.register("_rows", frame)
            if keys:
                condition = " AND ".join(f"t.{_q(key)} = r.{_q(key)}" for key in keys)
                con.execute(f"DELETE FROM {_q(table)} t WHERE EXISTS (SELECT 1 FROM _rows r WHERE {condition})")
            con.execute(f"INSERT INTO {_q(table)} SELECT {', '.join(_q(c) for c in columns)} FROM _rows")
            con.unregister("_rows")
        return len(frame)

    def read(self, table: str, where: str = "", params: list | None = None) -> pd.DataFrame:
        """表の行（``where`` は SQL の条件。``?`` に ``params`` を入れる）。"""
        with self._open() as con:
            sql = f"SELECT * FROM {_q(table)}" + (f" WHERE {where}" if where else "")
            return con.execute(sql, params or []).df()

    def delete(self, table: str, where: str, params: list | None = None) -> None:
        """条件に合う行を消す（買い目の記録を書き直すときなど）。"""
        with self._open() as con:
            con.execute(f"DELETE FROM {_q(table)} WHERE {where}", params or [])

    def as_of(self) -> date | None:
        """表3を書いた最後の開催日。まだ無ければ None。"""
        with self._open() as con:
            row = con.execute(f"SELECT max({_q(names.AS_OF)}) FROM {_q(names.COVERAGE_TABLE)}").fetchone()
        return row[0] if row and row[0] is not None else None

    def set_as_of(self, day: date) -> None:
        with self._open() as con:
            con.execute(f"DELETE FROM {_q(names.COVERAGE_TABLE)}")
            con.execute(f"INSERT INTO {_q(names.COVERAGE_TABLE)} VALUES (?)", [day])

    def _open(self) -> duckdb.DuckDBPyConnection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(self._path))
        for table, columns in _SCHEMAS.items():
            con.execute(f"CREATE TABLE IF NOT EXISTS {_q(table)} ({', '.join(f'{_q(name)} {kind}' for name, kind in columns)})")
        return con


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'
