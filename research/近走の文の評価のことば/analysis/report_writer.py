"""結果の表を Markdown にする。"""

from __future__ import annotations

from collections.abc import Sequence

from .label_tally import ADOPT_SIGMAS, LabelRow


class ReportWriter:
    """ことばの成績の行を、期間ごとの Markdown の表にする。"""

    def markdown(self, title: str, sections: Sequence[tuple[str, Sequence[LabelRow]]], notes: Sequence[str]) -> str:
        lines = [f"# {title}", ""]
        lines += [f"- {note}" for note in notes] + [""]
        for heading, rows in sections:
            lines += [f"## {heading}", "", "| ことば | 走 | 3着以内率 | 人気から見た差 | 標準誤差 | 単勝回収率 | 複勝回収率 | 採用 |",
                      "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |"]
            lines += [self._row(row) for row in rows]
            lines.append("")
        return "\n".join(lines)

    def _row(self, row: LabelRow) -> str:
        if row.runs == 0:
            return f"| {row.label} | 0 | — | — | — | — | — | — |"
        verdict = "—" if row.adopted is None else ("採用" if row.adopted else f"見送り（差が標準誤差の {ADOPT_SIGMAS:.0f}倍に届かない）")
        return (f"| {row.label} | {row.runs:,} | {row.place_rate:.1f}% | {row.gap_points:+.1f}pt | {row.std_error_points:.1f}pt "
                f"| {row.win_return:.0f}% | {row.place_return:.0f}% | {verdict} |")
