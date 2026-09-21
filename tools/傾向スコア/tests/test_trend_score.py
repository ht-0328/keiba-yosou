"""傾向スコアの CLI の契約: 表を出す、グラフ付きの HTML を1ファイルで書く、項目の一覧を出す、レースの指定を確かめる。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from 傾向スコア import trend_score
from 共通 import trend_html


def _run(*argv: str) -> None:
    trend_score.main(trend_score.build_parser().parse_args(list(argv)))


def test_writes_tables_and_a_standalone_html_page(trend_db: Path, tmp_path: Path):
    page, tables = tmp_path / "page.html", tmp_path / "tables.md"
    _run("--db", str(trend_db), "--date", "2025-04-19", "--venue", "東京", "--race", "2", "--condition", "良",
         "--min-runs", "3", "--min-z", "0", "--html", str(page), "--out", str(tables), "--detail")
    text = tables.read_text(encoding="utf-8")
    assert "### ランキング（点数の高い順）" in text and "### 馬ごとの内訳" in text and "| 1 | 4 | 4 | ウマ04 |" in text
    html = page.read_text(encoding="utf-8")
    assert "TrendView.render(" in html and "window.TrendView" in html and "<script src=" not in html  # 部品を埋めてあり、外を読まない
    data = json.loads(re.search(r'<script type="application/json" id="trend-data">(.*?)</script>', html, flags=re.DOTALL).group(1))
    assert data["horses"][0]["name"] == "ウマ04" and data["inputs"]["condition"] == "良" and data["options"]["min_runs"] == 3


def test_html_payload_cannot_close_its_script_tag():
    html = trend_html.standalone({"title": "</script><b>x", "horses": []})
    assert "</script><b>x" not in html and "\\u003c/script>" in html


def test_default_html_name_and_item_list(trend_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(trend_score, "REPORT_DIR", tmp_path / "reports")
    _run("--db", str(trend_db), "2025041905010102", "--html")
    assert (tmp_path / "reports" / "2025-04-19-東京-02R.html").exists()
    out = tmp_path / "items.csv"
    _run("--items", "--format", "csv", "--out", str(out))
    lines = out.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].startswith("項目,点,グループ") and len(lines) == 1 + 89 + 75 and lines[1].startswith("P01,+1,枠・馬番,枠番")


def test_race_must_be_specified(trend_db: Path):
    with pytest.raises(ValueError):
        _run("--db", str(trend_db), "--date", "2025-04-19")
    with pytest.raises(LookupError):
        _run("--db", str(trend_db), "2030010105010101")


def test_all_writes_a_page_per_race_and_an_index(trend_db: Path, tmp_path: Path):
    _run("--db", str(trend_db), "--date", "2025-04-19", "--all", "--html", str(tmp_path), "--condition", "良", "--min-runs", "3", "--min-z", "0")
    names = sorted(path.name for path in tmp_path.glob("*.html"))
    assert names == ["2025-04-19-index.html", "2025-04-19-東京-01R.html", "2025-04-19-東京-02R.html"]
    index = (tmp_path / "2025-04-19-index.html").read_text(encoding="utf-8")
    assert 'href="2025-04-19-東京-02R.html"' in index and "<li>4 ウマ04<span>" in index and "未入力" in index
    with pytest.raises(ValueError):
        _run("--db", str(trend_db), "--date", "2025-04-19", "--all", "--pops", "1:1")
    with pytest.raises(LookupError):
        _run("--db", str(trend_db), "--date", "2030-01-01", "--all")
