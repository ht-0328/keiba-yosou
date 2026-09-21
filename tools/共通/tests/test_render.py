"""整形の契約: Markdown の表・CSV・JSON、None と小数の見せ方。"""

from __future__ import annotations

import json
from pathlib import Path

from 共通 import render
from 共通.render import Table


def test_cell_text():
    assert render.cell_text(None) == ""
    assert render.cell_text(5.0) == "5"
    assert render.cell_text(5.4) == "5.4"
    assert render.cell_text(0.3333333) == "0.333"
    assert render.cell_text(True) == "はい"
    assert render.cell_text("x") == "x"


def test_markdown_table_escapes_pipes_and_marks_empty():
    table = Table(["a", "b"], [["x|y", None], [1, 2.5]], title="T", note="2 行")
    text = render.to_markdown(table)
    assert text.splitlines()[0] == "### T"
    assert "| x\\|y |  |" in text
    assert "| 1 | 2.5 |" in text
    assert text.endswith("2 行")
    assert "（該当なし）" in render.to_markdown(Table(["a"], []))


def test_csv_and_json_round_trip():
    table = Table(["a", "b"], [["x,y", None]], meta={"k": 1})
    assert render.to_csv(table) == 'a,b\n"x,y",\n'
    loaded = json.loads(render.to_json(table))
    assert loaded["columns"] == ["a", "b"] and loaded["rows"] == [["x,y", None]] and loaded["meta"] == {"k": 1}


def test_render_many_tables():
    tables = [Table(["a"], [[1]], title="1"), Table(["b"], [[2]], title="2")]
    assert render.render(tables, "markdown").count("### ") == 2
    assert render.render(tables, "json").startswith("[")


def test_write_csv_file_has_bom(tmp_path: Path):
    out = tmp_path / "x.csv"
    render.write("a,b\n", out, fmt="csv")
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    render.write("# md\n", tmp_path / "x.md", fmt="markdown")
    assert (tmp_path / "x.md").read_bytes() == "# md\n".encode()
