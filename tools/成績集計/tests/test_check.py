"""答え合わせの契約: ページの読み方、一致と不一致。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, perf
from 共通.filters import Filters
from 成績集計 import check

PAGE = """# 東京 芝 1600m

## 芝・左 1600m 稍重

### 単勝人気

| 単勝人気 | 出走数 | 着別度数 | 勝率 | 連対率 | 複勝率 | 馬券外率 | 単勝回収率 | 複勝回収率 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 9 | 9-0-0-0 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 100.0% |

## 芝・左 1600m 良

### 枠番

| 枠番 | 出走数 | 着別度数 | 勝率 | 連対率 | 複勝率 | 馬券外率 | 単勝回収率 | 複勝回収率 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 1 | 1-0-0-0 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 100.0% |

### 単勝人気

| 単勝人気 | 出走数 | 着別度数 | 勝率 | 連対率 | 複勝率 | 馬券外率 | 単勝回収率 | 複勝回収率 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | {cells} |
"""


def _page_from(cells: list[str]) -> str:
    return PAGE.format(cells=" | ".join(cells))


def test_read_expected_walks_section_then_table_then_row():
    expected = check.read_expected(_page_from(["4", "1-1-0-2", "25.0%", "50.0%", "50.0%", "50.0%", "50.0%", "55.0%"]))
    assert expected.runs == "4" and expected.counts == "1-1-0-2" and expected.rates[-1] == "55.0%"
    with pytest.raises(LookupError):
        check.read_expected("## ほか\n### 単勝人気\n| 1 | 2 |\n")


def test_run_check_ok_and_ng(synth_db: Path, tmp_path: Path):
    with db.open_db(synth_db) as con:
        rows = perf.perf_rows(con, perf.dimension("popularity"), Filters.from_mapping(check.CHECK_FILTERS))
        actual = perf.find_row(rows, 1).cells()
        good = tmp_path / "good.md"
        good.write_text(_page_from(actual), encoding="utf-8")
        result = check.run_check(con, page=good, date_from=None, date_to=None)
        assert result.ok and result.diffs == [] and check.check_table(result).note.startswith("OK")
        # 始まりの日より前は数えない（ページを作ったときの DB より古い年が DB に足されても、同じ期間で比べる）
        result = check.run_check(con, page=good, date_from="2999-01-01", date_to=None)
        assert not result.ok and result.diffs == ["集計に 1番人気 の行がありません"]
        wrong = list(actual)
        wrong[2] = "99.9%"
        bad = tmp_path / "bad.md"
        bad.write_text(_page_from(wrong), encoding="utf-8")
        result = check.run_check(con, page=bad, date_from=None, date_to=None)
        assert not result.ok and result.diffs == [f"勝率: 期待 99.9% ← 実際 {actual[2]}"]
        assert check.check_table(result).rows[2][3] == "NG"
        with pytest.raises(FileNotFoundError):
            check.run_check(con, page=tmp_path / "none.md")
