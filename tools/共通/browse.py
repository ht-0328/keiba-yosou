"""元DB を表の単位で覗く。DB の状態、表の一覧と中身、任意の SQL。

予想や集計には使わない。**取ったデータが本当に入っているかを目で確かめる**ためのもの。
表名・列名は必ず実在するものと突き合わせてから SQL に埋める（画面から来た文字をそのまま識別子にしない）。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from . import keys
from .render import Table

#: 1度に返す列の上限。親の表は 200 列ほどあり、全部返すと画面が固まる。
MAX_COLUMNS = 60
#: 画面で1度に返す行の上限。
WEB_MAX_ROWS = 200
#: CLI で1度に返す行の上限。
CLI_MAX_ROWS = 100_000
#: 内部用の表（``_tables``・``_meta``）の印。一覧に出さない。
_HIDDEN_PREFIX = "_"
#: 親の表と繰返しブロックの子の表の区切り（``o1__単勝オッズ``）。
_BLOCK_SEPARATOR = "__"
#: 開催日で絞るために要る列。
_DATE_COLUMNS = ("開催年", "開催月日")
#: 任意 SQL で許す文の先頭。読むだけの文。
READ_STATEMENTS: tuple[str, ...] = ("SELECT", "WITH", "FROM", "DESCRIBE", "SHOW", "SUMMARIZE", "EXPLAIN", "PRAGMA")
#: 結果を LIMIT で包める文（それ以外は Python 側で切る）。
_WRAPPABLE = ("SELECT", "WITH", "FROM")
#: 任意 SQL の時間の上限（秒）。
DEFAULT_TIMEOUT_SECONDS = 60.0
#: 途中の年から入っている表。DB の状態で最初の開催日を出す。
OPTIONAL_TABLES: tuple[tuple[str, str], ...] = (
    ("dm", "タイム型マイニング予想"), ("tm", "対戦型マイニング予想"), ("ck", "出走別着度数"),
)


@dataclass(frozen=True)
class TableInfo:
    """表1つの概要。"""

    name: str
    record_id: str
    title: str
    rows: int
    rows_in_range: int | None
    columns: int
    date_from: str | None
    date_to: str | None


def _format_date(raw: str | None) -> str | None:
    """``20260301`` を ``2026-03-01`` に。桁が違えばそのまま。"""
    if not raw or len(raw) != 8 or not raw.isdigit():
        return raw or None
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def _compact_date(text: str) -> str:
    """``2026-03-01`` を ``20260301`` に。"""
    return text.replace("-", "")


def _record_id(name: str) -> str:
    """表名からレコード種別ID（大文字）へ。子の表は親のもの。"""
    return name.partition(_BLOCK_SEPARATOR)[0].upper()


class TableBrowser:
    """1つの DB を表の単位で読む。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con
        self._titles: dict[str, str] | None = None

    def names(self) -> list[str]:
        """実在する表の名前。SQL に埋めてよいのはここに載っているものだけ。"""
        return [
            name for (name,) in self.con.execute(
                "SELECT table_name FROM duckdb_tables() WHERE NOT starts_with(table_name, ?) ORDER BY table_name",
                [_HIDDEN_PREFIX],
            ).fetchall()
        ]

    def has_table(self, name: str) -> bool:
        """その名前の表があるか（内部用の表も含む）。"""
        return bool(self.con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = ?", [name]).fetchone()[0])

    def first_table(self, parent: str) -> str | None:
        """親の表があればその名前、無ければ子の表（``tm__マイニング予想``）の最初の名前。どちらも無ければ None。"""
        for name in self.names():
            if name == parent or name.startswith(parent + _BLOCK_SEPARATOR):
                return name
        return None

    def titles(self) -> dict[str, str]:
        """親の表の表題（``_tables`` から）。無ければ空。"""
        if self._titles is None:
            self._titles = dict(self.con.execute("SELECT table_name, title FROM _tables").fetchall()) if self.has_table("_tables") else {}
        return self._titles

    def title(self, name: str) -> str:
        """``o1__単勝オッズ`` なら「オッズ1（単複枠） › 単勝オッズ」。"""
        parent, _, block = name.partition(_BLOCK_SEPARATOR)
        title = self.titles().get(parent, parent.upper())
        return f"{title} › {block}" if block else title

    def columns(self, name: str) -> list[str]:
        """表の列（定義順）。"""
        self._require(name)
        return [
            column for (column,) in self.con.execute(
                "SELECT column_name FROM duckdb_columns() WHERE table_name = ? ORDER BY column_index", [name]
            ).fetchall()
        ]

    def describe(self, name: str) -> Table:
        """列の一覧（番号・列名・型）。"""
        self._require(name)
        # 表題を先に決める。表題の読み出しも同じ接続に SQL を打つので、下の結果を読む前に打つと結果が入れ替わる
        title = f"{name}（{self.title(name)}）の列"
        cursor = self.con.execute(
            "SELECT column_index AS 番号, column_name AS 列, data_type AS 型 FROM duckdb_columns() "
            "WHERE table_name = ? ORDER BY column_index", [name],
        )
        return Table.from_cursor(cursor, title=title)

    def list_tables(self, date_from: str | None = None, date_to: str | None = None) -> list[TableInfo]:
        """表の一覧。期間を渡すと、その期間に入る行数も数える。"""
        return [self._info(name, date_from, date_to) for name in self.names()]

    def _info(self, name: str, date_from: str | None, date_to: str | None) -> TableInfo:
        columns = self.columns(name)
        rows = self.con.execute(f"SELECT count(*) FROM {keys.q(name)}").fetchone()[0]
        oldest = newest = None
        in_range = None
        date_expression = self._date_expression(columns)
        if date_expression and rows:
            oldest, newest = self.con.execute(
                f"SELECT min({date_expression}), max({date_expression}) FROM {keys.q(name)}"
            ).fetchone()
            if date_from or date_to:
                where, params = self._where(columns, date_from, date_to, None)
                in_range = self.con.execute(f"SELECT count(*) FROM {keys.q(name)} {where}", params).fetchone()[0]
        return TableInfo(
            name=name, record_id=_record_id(name), title=self.title(name), rows=rows, rows_in_range=in_range,
            columns=len(columns), date_from=_format_date(oldest), date_to=_format_date(newest),
        )

    def read(self, name: str, *, limit: int = 50, offset: int = 0, column_offset: int = 0,
             columns: list[str] | None = None, date_from: str | None = None, date_to: str | None = None,
             equals: dict[str, str] | None = None, max_rows: int = WEB_MAX_ROWS) -> dict[str, Any]:
        """1つの表を読む。列も行も上限で切り、切ったことを呼び手に伝える。"""
        all_columns = self.columns(name)
        limit = max(1, min(int(limit), max_rows))
        offset = max(0, int(offset))
        if columns:
            unknown = [c for c in columns if c not in all_columns]
            if unknown:
                raise LookupError(f"表 {name} に無い列です: {', '.join(unknown)}")
            chosen = list(columns)
            column_offset = 0
        else:
            column_offset = max(0, min(int(column_offset), max(0, len(all_columns) - 1)))
            chosen = all_columns[column_offset:column_offset + MAX_COLUMNS]
        where, params = self._where(all_columns, date_from, date_to, equals)
        total = self.con.execute(f"SELECT count(*) FROM {keys.q(name)} {where}", params).fetchone()[0]
        select = ", ".join(keys.q(c) for c in chosen)
        order = ", ".join(keys.q(c) for c in self._order_columns(all_columns))
        rows = self.con.execute(
            f"SELECT {select} FROM {keys.q(name)} {where} ORDER BY {order} LIMIT ? OFFSET ?", [*params, limit, offset]
        ).fetchall()
        return {
            "name": name, "record_id": _record_id(name), "title": self.title(name),
            "columns": chosen, "rows": [list(row) for row in rows], "total": total, "offset": offset,
            "limit": limit, "column_total": len(all_columns), "column_offset": column_offset,
            "filterable_by_date": self._date_expression(all_columns) is not None,
        }

    def _require(self, name: str) -> None:
        if name not in self.names():
            raise LookupError(f"知らない表です: {name}（--list で一覧が見られます）")

    @staticmethod
    def _date_expression(columns: list[str]) -> str | None:
        """開催日で絞れる表なら、日付を作る式。馬・騎手のマスタは絞れない。"""
        if not all(column in columns for column in _DATE_COLUMNS):
            return None
        return f"{keys.q('開催年')} || {keys.q('開催月日')}"

    @staticmethod
    def _order_columns(columns: list[str]) -> list[str]:
        """並び順。鍵の列があればそれ、無ければ最初の列。収録順序は当てにできない。"""
        chosen = [name for name in (*keys.RACE_KEY, "_連番", "馬番", keys.HORSE_KEY) if name in columns]
        return chosen or columns[:1]

    def _where(self, columns: list[str], date_from: str | None, date_to: str | None,
               equals: dict[str, str] | None) -> tuple[str, list[str]]:
        """開催日と 列=値 の条件。列名は実在するものだけ通す。"""
        clauses: list[str] = []
        params: list[str] = []
        date_expression = self._date_expression(columns)
        if date_expression and date_from:
            clauses.append(f"{date_expression} >= ?")
            params.append(_compact_date(date_from))
        if date_expression and date_to:
            clauses.append(f"{date_expression} <= ?")
            params.append(_compact_date(date_to))
        for column, value in (equals or {}).items():
            if column not in columns:
                raise LookupError(f"無い列です: {column}")
            clauses.append(f"{keys.q(column)} = ?")
            params.append(value)
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params


def tables_table(infos: list[TableInfo]) -> Table:
    """表の一覧を表にする。"""
    columns = ["表", "表題", "行数", "期間内の行数", "列数", "最初の開催日", "最後の開催日"]
    rows = [[i.name, i.title, i.rows, i.rows_in_range, i.columns, i.date_from, i.date_to] for i in infos]
    return Table(columns, rows, title="表の一覧")


def rows_table(result: dict[str, Any]) -> Table:
    """``TableBrowser.read`` の結果を表にする。"""
    first = result["offset"] + 1
    last = result["offset"] + len(result["rows"])
    shown = f"{first}〜{last} 行" if result["rows"] else "該当なし"
    note = f"全 {result['total']:,} 行のうち {shown}、全 {result['column_total']} 列のうち {len(result['columns'])} 列"
    return Table(result["columns"], result["rows"], title=f"{result['name']}（{result['title']}）", note=note)


def parse_equals(texts: list[str]) -> dict[str, str]:
    """``列=値`` の並びを辞書にする。"""
    out: dict[str, str] = {}
    for text in texts:
        column, separator, value = text.partition("=")
        if not separator or not column.strip():
            raise ValueError(f"--where は 列=値 の形で書いてください: {text}")
        out[column.strip()] = value
    return out


# ------------------------------------------------------------------ DB の状態

@dataclass(frozen=True)
class DbStatus:
    """DB の概要。"""

    path: str
    size_mb: float
    tables: int
    race_range: tuple[str | None, str | None]
    final_races: int
    final_runs: int
    optional_from: dict[str, str | None]
    meta: dict[str, str]


def db_status(con: duckdb.DuckDBPyConnection, path: Path) -> DbStatus:
    """DB の大きさ・表の数・中央の確定成績の期間と件数・途中から入っている表・同期の記録。"""
    browser = TableBrowser(con)
    date_expr = f"{keys.q('開催年')} || {keys.q('開催月日')}"
    race_range: tuple[str | None, str | None] = (None, None)
    final_races = final_runs = 0
    if browser.has_table("ra"):
        low, high, final_races = con.execute(
            f"SELECT min({date_expr}), max({date_expr}), count(DISTINCT {keys.rid_expr()}) FROM ra "
            f"WHERE {keys.jra_only()} AND {keys.final_only()}"
        ).fetchone()
        race_range = (_format_date(low), _format_date(high))
    if browser.has_table("se"):
        final_runs = con.execute(
            f"SELECT count(*) FROM se WHERE {keys.jra_only()} AND {keys.final_only()} "
            f"AND {keys.q('異常区分コード')} NOT IN {keys.sql_list(keys.NOT_RAN_CODES)}"
        ).fetchone()[0]
    optional_from: dict[str, str | None] = {}
    for name, title in OPTIONAL_TABLES:
        first = None
        present = browser.first_table(name)
        if present:
            first = con.execute(f"SELECT min({date_expr}) FROM {keys.q(present)} WHERE {keys.jra_only()}").fetchone()[0]
        optional_from[title] = _format_date(first)
    meta = dict(con.execute("SELECT key, value FROM _meta ORDER BY key").fetchall()) if browser.has_table("_meta") else {}
    size_mb = round(path.stat().st_size / 1_000_000, 1) if path.exists() else 0.0
    return DbStatus(str(path), size_mb, len(browser.names()), race_range, final_races, final_runs, optional_from, meta)


def year_counts(con: duckdb.DuckDBPyConnection) -> Table:
    """年ごとの中央・確定成績のレース数と出走数。孤立した古い年や、取り込み途中の年に気づくための表。"""
    browser = TableBrowser(con)
    if not browser.has_table("ra"):
        return Table(["年", "レース数", "出走数"], [], title="年ごとのレース数（中央・確定成績）")
    runs_sql = (
        f"SELECT {keys.q('開催年')} AS y, count(*) AS n FROM se WHERE {keys.jra_only()} AND {keys.final_only()} "
        f"AND {keys.q('異常区分コード')} NOT IN {keys.sql_list(keys.NOT_RAN_CODES)} GROUP BY 1"
    ) if browser.has_table("se") else "SELECT NULL AS y, NULL AS n WHERE FALSE"
    cursor = con.execute(
        f"SELECT r.y AS 年, r.n AS レース数, coalesce(s.n, 0) AS 出走数 FROM ("
        f"SELECT {keys.q('開催年')} AS y, count(DISTINCT {keys.rid_expr()}) AS n FROM ra "
        f"WHERE {keys.jra_only()} AND {keys.final_only()} GROUP BY 1) r LEFT JOIN ({runs_sql}) s ON s.y = r.y ORDER BY 1"
    )
    return Table.from_cursor(cursor, title="年ごとのレース数（中央・確定成績）")


def status_table(status: DbStatus) -> Table:
    """DB の状態を「項目 | 値」の縦表にする。"""
    rows: list[list[Any]] = [
        ["DB", status.path], ["大きさ（MB）", status.size_mb], ["表の数", status.tables],
        ["中央・確定成績の期間", f"{status.race_range[0] or '—'} 〜 {status.race_range[1] or '—'}"],
        ["中央・確定成績のレース数", status.final_races],
        ["中央・確定成績の出走数（取消・除外を除く）", status.final_runs],
    ]
    for title, first in status.optional_from.items():
        rows.append([f"{title} の最初の開催日", first or "（表が無い）"])
    for key, value in status.meta.items():
        rows.append([f"同期 {key}", value])
    return Table(["項目", "値"], rows, title="DB の状態")


# ------------------------------------------------------------------ 任意 SQL

def _first_keyword(sql: str) -> str:
    """文の最初の語（大文字）。"""
    stripped = sql.lstrip("( \n\t")
    return stripped.split(None, 1)[0].upper() if stripped else ""


def _single_statement(sql: str) -> str:
    """末尾の ``;`` と空白を落とし、途中に ``;`` があれば断る。"""
    text = sql.strip().rstrip(";").strip()
    if not text:
        raise ValueError("SQL が空です")
    if ";" in text:
        raise ValueError("SQL は1文だけ実行できます（途中に ; があります）")
    return text


def run_sql(con: duckdb.DuckDBPyConnection, sql: str, *, limit: int = WEB_MAX_ROWS,
            timeout_s: float = DEFAULT_TIMEOUT_SECONDS) -> Table:
    """読むだけの SQL を1文実行して表にする。``limit`` 行で切り、時間の上限を越えたら止める。

    接続は読み取り専用なので書き込みはもともとできない。ここでは、読む文以外を断り、
    結果を ``LIMIT`` で包み、長い問い合わせを ``interrupt`` で止める。
    """
    statement = _single_statement(sql)
    keyword = _first_keyword(statement)
    if keyword not in READ_STATEMENTS:
        raise ValueError(f"実行できるのは読む文（{', '.join(READ_STATEMENTS)}）だけです: {keyword or statement[:20]}")
    limit = max(1, int(limit))
    query = f"SELECT * FROM ({statement}) AS q LIMIT {limit + 1}" if keyword in _WRAPPABLE else statement
    timer = threading.Timer(timeout_s, con.interrupt)
    started = time.perf_counter()
    timer.start()
    try:
        table = Table.from_cursor(con.execute(query))
    except duckdb.InterruptException:
        raise TimeoutError(f"{timeout_s:g} 秒を越えたので止めました。条件を絞るか --timeout を延ばしてください。") from None
    finally:
        timer.cancel()
    elapsed = round(time.perf_counter() - started, 2)
    truncated = len(table.rows) > limit
    table.rows = table.rows[:limit]
    table.meta = {"truncated": truncated, "elapsed_s": elapsed, "limit": limit}
    table.note = f"{len(table.rows)} 行（{elapsed} 秒）" + (
        "。上限で打ち切りました。続きは --limit を増やしてください。" if truncated else ""
    )
    return table
