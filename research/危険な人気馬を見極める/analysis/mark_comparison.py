"""道具「印の成績」の結果を作り方ごとに読み、買い方ごとの回収率と的中率を横に並べる表。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from 共通.render import Table

#: 印の成績の結果のうち、買い方ごとの買い目の成績の表の見出しと、読む対象（全レース）。
_SECTION = "### 7. 買い方ごとの買い目の成績"
_TARGET = "全レース"
#: 表の列の位置（買い方・対象・回収率・的中率）。
_NAME, _SCOPE, _RETURN, _HIT = 0, 1, 7, 10
#: 消の成績を読む行の名前（表1 の印ごとの成績）。
_DANGER_ROWS = ("消のうち 1番人気", "消のうち 2〜5番人気")


class MarkComparison:
    """作り方ごとの印の成績（``reports/…/印の成績/<作り方>/<全頭の予想>.md``）を読み、全レースの買い方ごとに、
    回収率と的中率を作り方の順に並べる。どの合計（元の買い目だけ・◎軸・軸馬）も同じ表に出る。
    """

    def tables(self, reports: Mapping[str, Path]) -> list[Table]:
        """``reports`` は 作り方の名前 → 印の成績の結果のファイル（Markdown）。"""
        parsed = {name: self._bets(path.read_text(encoding="utf-8")) for name, path in reports.items()}
        names = list(parsed)
        order = list(next(iter(parsed.values()))) if parsed else []
        rows = [[bet, *(parsed[name].get(bet, ("", ""))[i] for name in names for i in (0, 1))] for bet in order]
        columns = ["買い方", *(f"{name} {kind}" for name in names for kind in ("回収率", "的中率"))]
        dangers = [[name, *self._danger(path.read_text(encoding="utf-8"))] for name, path in reports.items()]
        return [
            Table(columns, rows, title="買い方ごとの回収率と的中率（全レース・テスト期間）"),
            Table(["作り方", "消のうち 1番人気（頭数・3着以内率）", "消のうち 2〜5番人気（頭数・3着以内率）"], dangers,
                  title="消を付けた人気馬の成績"),
        ]

    def _bets(self, text: str) -> dict[str, tuple[str, str]]:
        """全レースの行の 買い方 → （回収率, 的中率）。"""
        section = text.split(_SECTION, 1)[1].split("\n### ", 1)[0]
        cells = [line.strip("|").split("|") for line in section.splitlines() if line.startswith("| ")]
        return {row[_NAME].strip(): (row[_RETURN].strip(), row[_HIT].strip())
                for row in cells if len(row) > _HIT and row[_SCOPE].strip() == _TARGET}

    def _danger(self, text: str) -> list[str]:
        """消のうち1番人気・2〜5番人気の、頭数と3着以内率（消を使わない作り方では空）。"""
        values = []
        for name in _DANGER_ROWS:
            line = next((line for line in text.splitlines() if line.startswith(f"| {name} |")), None)
            cells = line.strip("|").split("|") if line else []
            values.append(f"{cells[2].strip()}頭・{cells[6].strip()}" if len(cells) > 6 else "")
        return values
