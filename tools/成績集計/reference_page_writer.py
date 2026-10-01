"""基準のページ（コースの単位ごとの成績）を書く。1ページ = 競馬場×芝ダ×距離、節 = コース×馬場状態。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import codes

from 成績集計.reference_runs import UNKNOWN_GOING
from 成績集計.reference_sections import SECTION_TABLES
from 成績集計.reference_tally import ReferenceTally

#: ページ・節の見出しと、成績を数えるのに要る列（表ごとの列のほかに）。
_BASE_COLUMNS: tuple[str, ...] = (
    "rid", "race_date", "venue_code", "surface", "distance", "track_code", "course", "going",
    "first", "second", "third", "win_yen", "place_yen",
)
#: 馬場状態の並び。
GOING_ORDER: tuple[str, ...] = ("良", "稍重", "重", "不良", UNKNOWN_GOING)


class ReferencePageWriter:
    """``ReferenceRuns``（と ``ReferenceLabels``）の表から、コースの単位ごとのページを ``out_dir`` に書く。書いたページのパスを返す。

    各節には ``reference_sections.SECTION_TABLES`` の表を上から順に置く。

    ファイル名は ``<競馬場コード>-<turf|dirt|jump>-<距離>.md``（例 ``05-turf-1600.md``）。
    """

    def __init__(self, tally: ReferenceTally, made_on: str) -> None:
        self._tally = tally
        self._made_on = made_on

    def write(self, runs: pd.DataFrame, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        # 表を作るたびに行を写すので、要る列だけにしておく（列が多いと遅い）
        used = dict.fromkeys([*_BASE_COLUMNS, *(column for table in SECTION_TABLES for column in table.used_columns())])
        runs = runs[list(used)]
        written = []
        for (venue, surface, distance), page_runs in runs.groupby(["venue_code", "surface", "distance"]):
            path = out_dir / page_name(venue, surface, distance)
            path.write_text(self.page_text(venue, surface, int(distance), page_runs), encoding="utf-8")
            written.append(path)
        return written

    def page_text(self, venue: str, surface: str, distance: int, runs: pd.DataFrame) -> str:
        sections = _ordered_sections(runs)
        lines = [
            f"# {codes.venue_name(venue)} {surface} {distance}m", "",
            f"{codes.venue_name(venue)}競馬場 {surface} {distance}m の成績を、コース×馬場状態ごとに数えたもの。",
            f"見方は [基礎統計の目次](index.md) にある。`tools/成績集計/build_pages.py` が作る（作成日 {self._made_on}）。"
            "**手で直さない。**", "",
            "| コース | 馬場状態 | レース数 | 延べ頭数 |", "| :--- | :--- | :--- | :--- |",
            *(f"| {course} | {going} | {part['rid'].nunique():,} | {len(part):,} |" for (course, going), part in sections),
            "", "---",
        ]
        for (course, going), part in sections:
            lines.extend(self._section_lines(f"{course} {distance}m {going}", part))
        return "\n".join(lines) + "\n"

    def _section_lines(self, title: str, runs: pd.DataFrame) -> list[str]:
        lines = ["", f"## {title}", "", f"{runs['rid'].nunique():,} レース・延べ {len(runs):,} 頭。"]
        for table in SECTION_TABLES:
            lines.extend(table.lines(runs, self._tally))
        return lines


def page_name(venue: str, surface: str, distance) -> str:
    return f"{venue}-{codes.SURFACE_SLUG[surface]}-{int(distance)}.md"


def _ordered_sections(runs: pd.DataFrame) -> list[tuple[tuple[str, str], pd.DataFrame]]:
    """節（コース×馬場状態）を、トラックコードの順・馬場状態の順に並べる。"""
    order = {going: index for index, going in enumerate(GOING_ORDER)}
    groups = runs.groupby(["track_code", "course", "going"])
    keys = sorted(groups.groups, key=lambda key: (key[0], order.get(key[2], len(order))))
    return [((course, going), groups.get_group((track, course, going))) for track, course, going in keys]
