"""集計や検索の結果を、人が読む形（Markdown の表）と機械が読む形（CSV / JSON）にする。

率や回収率の見た目（``38.4%``）は集計側（``perf``）で文字にしてから渡す。ここは値をそのまま並べるだけ。
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: 選べる出力形式。
FORMATS: tuple[str, ...] = ("markdown", "csv", "json")
DEFAULT_FORMAT = "markdown"
#: 表を横に並べるときの区切り（Markdown の表を続けて出す）。
_TABLE_GAP = "\n\n"


@dataclass
class Table:
    """1つの表。``columns`` が見出し、``rows`` が値の並び（1行 = 1リスト）。"""

    columns: list[str]
    rows: list[list[Any]]
    title: str = ""
    note: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_cursor(cls, cursor: Any, *, title: str = "", note: str = "") -> "Table":
        """DuckDB のカーソルから作る（列名は ``description`` から）。"""
        columns = [description[0] for description in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
        return cls(columns, rows, title=title, note=note)

    @classmethod
    def from_records(cls, records: Sequence[dict[str, Any]], columns: Sequence[str] | None = None, *,
                     title: str = "", note: str = "") -> "Table":
        """辞書の並びから作る。列は最初の行の鍵（または ``columns``）。"""
        names = list(columns) if columns else (list(records[0]) if records else [])
        return cls(names, [[record.get(name) for name in names] for record in records], title=title, note=note)

    def __len__(self) -> int:
        return len(self.rows)


def cell_text(value: Any) -> str:
    """セルに入れる文字。None は空、小数は末尾の 0 を落とす。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.3f}".rstrip("0")
    return str(value)


def _markdown_cell(value: Any) -> str:
    """Markdown の表のセル。縦棒と改行を潰す。"""
    return cell_text(value).replace("|", "\\|").replace("\n", " ")


def to_markdown(table: Table) -> str:
    """Markdown の表。``title`` があれば ``###`` の見出し、``note`` があれば表の下に1行。"""
    lines: list[str] = []
    if table.title:
        lines.append(f"### {table.title}")
        lines.append("")
    if table.columns:
        lines.append("| " + " | ".join(_markdown_cell(c) for c in table.columns) + " |")
        lines.append("|" + " :--- |" * len(table.columns))
        for row in table.rows:
            lines.append("| " + " | ".join(_markdown_cell(v) for v in row) + " |")
    if not table.rows:
        lines.append("（該当なし）")
    if table.note:
        lines.append("")
        lines.append(table.note)
    return "\n".join(lines)


def to_csv(table: Table) -> str:
    """CSV（見出し行 + 値）。``title``・``note`` は入れない。"""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(table.columns)
    for row in table.rows:
        writer.writerow([cell_text(v) for v in row])
    return buffer.getvalue()


def _json_default(value: Any) -> Any:
    """JSON にできない値（Decimal・日付）は文字にする。"""
    return str(value)


def to_json(table: Table) -> str:
    """JSON。``{"title", "columns", "rows", "note", "meta"}``。"""
    return json.dumps(
        {"title": table.title, "columns": table.columns, "rows": table.rows, "note": table.note, "meta": table.meta},
        ensure_ascii=False, default=_json_default,
    )


def render(result: Table | Sequence[Table], fmt: str = DEFAULT_FORMAT) -> str:
    """表（または表の並び）を指定の形式の文字にする。"""
    if fmt not in FORMATS:
        raise ValueError(f"出力形式は {', '.join(FORMATS)} のどれかです: {fmt}")
    tables = [result] if isinstance(result, Table) else list(result)
    if fmt == "markdown":
        return _TABLE_GAP.join(to_markdown(t) for t in tables) + "\n"
    if fmt == "csv":
        return "\n".join(to_csv(t) for t in tables)
    if len(tables) == 1:
        return to_json(tables[0]) + "\n"
    return "[" + ", ".join(to_json(t) for t in tables) + "]\n"


def write(text: str, out: Path | None, *, fmt: str = DEFAULT_FORMAT) -> None:
    """標準出力か、``out`` のファイルへ書く。CSV のファイルは Excel が開ける BOM 付き UTF-8。"""
    if out is None:
        sys.stdout.write(text)
        sys.stdout.flush()
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if fmt == "csv" else "utf-8"
    out.write_text(text, encoding=encoding, newline="\n")
