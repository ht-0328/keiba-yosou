"""基準のページを作る道具の契約: 別の道筋で数えた値が perf の集計と一致すること、数え方の約束、期間の絞り込み。"""

from __future__ import annotations

from pathlib import Path

from 共通 import db
from 成績集計 import check
from 成績集計.reference_index_writer import ReferenceIndexWriter
from 成績集計.reference_page_writer import ReferencePageWriter
from 成績集計.reference_runs import ReferenceRuns
from 成績集計.reference_tally import ReferenceTally
from 成績集計.repository import FinalRunnerRepository, PayoutRepository


def _build(database: Path, out_dir: Path, date_from: str | None = None, date_to: str | None = None):
    with db.open_db(database) as con:
        runs = ReferenceRuns().build(FinalRunnerRepository(con).read(date_from, date_to), PayoutRepository(con).read())
    ReferencePageWriter(ReferenceTally(), "2026-09-30").write(runs, out_dir)
    ReferenceIndexWriter("2026-09-30").write(runs, out_dir)
    return runs


def _table(page: str, section: str, title: str) -> dict[str, list[str]]:
    """節 → 表 をたどって、先頭のセル → 残りのセル の辞書にする。"""
    lines = page.split(f"## {section}\n", 1)[1].split(f"### {title}\n", 1)[1].split("\n###", 1)[0].splitlines()
    cells = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines if line.startswith("|")]
    return {row[0]: row[1:] for row in cells[2:]}


def test_the_page_agrees_with_perf_on_the_check_row(synth_db: Path, tmp_path: Path):
    """答え合わせの行（東京 芝・左 1600m 良 の1番人気）が、perf の集計と一致する。"""
    _build(synth_db, tmp_path)
    with db.open_db(synth_db) as con:
        result = check.run_check(con, page=tmp_path / "05-turf-1600.md", date_from=None, date_to=None)
    assert result.ok, result.diffs


def test_scratched_horses_are_not_counted_and_stopped_horses_are_out(one_race_db: Path, tmp_path: Path):
    """取消（馬番6）は出走に数えない。競走中止（馬番5）は出走して馬券外。払戻は勝ち馬・3着以内の馬にだけ付く。"""
    _build(one_race_db, tmp_path)
    numbers = _table((tmp_path / "05-turf-1600.md").read_text(encoding="utf-8"), "芝・左 1600m 良", "馬番")
    assert sorted(numbers) == ["1", "2", "3", "4", "5"]
    assert numbers["5"][:2] == ["1", "0-0-0-1"]
    assert numbers["4"][:2] == ["1", "1-0-0-0"] and numbers["4"][-2:] == ["1500.0%", "400.0%"]
    assert numbers["1"][-2:] == ["0.0%", "0.0%"], "1番人気は4着（払戻なし）"


def test_the_period_limits_the_races(synth_db: Path, tmp_path: Path):
    runs = _build(synth_db, tmp_path, date_from="2025-01-01", date_to=None)
    assert runs["race_date"].min() == "2025-04-12" and runs["rid"].nunique() == 1
    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "2025-04-12 〜 2025-04-12" in index and "[芝 1600m](05-turf-1600.md)" in index
