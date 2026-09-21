"""答え合わせ: ``reports/stats`` のページに載っている成績と、``perf`` の集計を突き合わせる。

基準は **東京 芝・左 1600m 良 の1番人気** の成績7つ。ページ（``reports/stats/05-turf-1600.md``）の
``## 芝・左 1600m 良`` → ``### 単勝人気`` → 先頭セルが ``1`` の行を読み、同じ条件で集計した値と比べる。
新しい集計を作ったら、ここが一致することを確かめてから先へ進む。

ページは元DB のある時点で作られたもの。DB を取り直して値が変わったら、ページを作り直すか ``--to`` を合わせる。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import perf  # noqa: E402
from 共通.filters import Filters  # noqa: E402
from 共通.render import Table  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
#: 答え合わせに使うページと、その中の節・表・行。
CHECK_PAGE = ROOT / "reports" / "stats" / "05-turf-1600.md"
CHECK_SECTION = "芝・左 1600m 良"
CHECK_TABLE = "単勝人気"
CHECK_LABEL = "1"
#: ページを作ったときの DB の最後の開催日。これより後の日は数えない。
CHECK_DATE_TO = "2026-09-12"
#: ページの節に対応する絞り込み。
CHECK_FILTERS = {"venue": "05", "course": "芝・左", "distance": "1600", "condition": "良"}
CHECK_DIMENSION = "popularity"

_SECTION_PREFIX = "## "
_TABLE_PREFIX = "### "


@dataclass(frozen=True)
class Expected:
    """ページに書いてある成績（表のセルの文字のまま）。"""

    runs: str
    counts: str
    rates: tuple[str, ...]

    def cells(self) -> list[str]:
        return [self.runs, self.counts, *self.rates]


@dataclass(frozen=True)
class CheckResult:
    """答え合わせの結果。``diffs`` が空なら一致。"""

    ok: bool
    expected: list[str]
    actual: list[str]
    diffs: list[str]
    describe: str


def _cells(line: str) -> list[str]:
    """Markdown の表の1行をセルに分ける。"""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def read_expected(text: str, section: str = CHECK_SECTION, table: str = CHECK_TABLE, label: str = CHECK_LABEL) -> Expected:
    """ページの文字から、節 → 表 → 行 をたどって成績を読む。無ければ ``LookupError``。"""
    in_section = in_table = False
    for line in text.splitlines():
        if line.startswith(_SECTION_PREFIX):
            in_section = line[len(_SECTION_PREFIX):].strip() == section
            in_table = False
            continue
        if in_section and line.startswith(_TABLE_PREFIX):
            in_table = line[len(_TABLE_PREFIX):].strip() == table
            continue
        if in_section and in_table and line.startswith("|"):
            cells = _cells(line)
            if cells and cells[0] == label and len(cells) == 1 + len(perf.PERF_COLUMNS):
                return Expected(cells[1], cells[2], tuple(cells[3:]))
    raise LookupError(f"ページに 節「{section}」→ 表「{table}」→ 行「{label}」が見つかりません")


def compare(expected: Expected, actual: perf.PerfRow) -> list[str]:
    """期待と実際を列ごとに比べ、違う列の説明を返す。空なら一致。"""
    diffs: list[str] = []
    for name, want, got in zip(perf.PERF_COLUMNS, expected.cells(), actual.cells()):
        if want != got:
            diffs.append(f"{name}: 期待 {want} ← 実際 {got}")
    return diffs


def run_check(con: duckdb.DuckDBPyConnection, *, page: Path = CHECK_PAGE, date_to: str | None = CHECK_DATE_TO) -> CheckResult:
    """ページを読み、同じ条件で集計して比べる。"""
    if not page.exists():
        raise FileNotFoundError(f"答え合わせのページがありません: {page}")
    expected = read_expected(page.read_text(encoding="utf-8"))
    filters = Filters.from_mapping({**CHECK_FILTERS, "to": date_to})
    rows = perf.perf_rows(con, perf.dimension(CHECK_DIMENSION), filters)
    actual = perf.find_row(rows, CHECK_LABEL)
    describe = f"{filters.describe()} {CHECK_LABEL}番人気"
    if actual is None:
        return CheckResult(False, expected.cells(), [], [f"集計に {CHECK_LABEL}番人気 の行がありません"], describe)
    diffs = compare(expected, actual)
    return CheckResult(not diffs, expected.cells(), actual.cells(), diffs, describe)


def check_table(result: CheckResult) -> Table:
    """結果を「列 | 期待 | 実際 | 一致」の表にする。"""
    rows = []
    for name, want, got in zip(perf.PERF_COLUMNS, result.expected, result.actual or [""] * len(perf.PERF_COLUMNS)):
        rows.append([name, want, got, "OK" if want == got else "NG"])
    verdict = "OK 一致" if result.ok else "NG 不一致: " + " / ".join(result.diffs)
    return Table(["列", "期待（ページ）", "実際（集計）", "一致"], rows, title=f"答え合わせ: {result.describe}", note=verdict)
