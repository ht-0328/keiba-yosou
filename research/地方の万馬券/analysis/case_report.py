"""事例の報告: 表をまとめて ``reports/地方の万馬券/事例.md`` に書く。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from 共通 import render
from 共通.render import Table


@dataclass(frozen=True)
class CaseReport:
    """見出しと注を付けて、表を1つの Markdown に並べる。"""

    out_dir: Path

    def write(self, name: str, heading: str, intro: str, tables: list[Table]) -> Path:
        """``name``.md に書き、書いた場所を返す。"""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"{name}.md"
        body = "\n\n".join(render.to_markdown(table) for table in tables)
        path.write_text(f"# {heading}\n\n{intro}\n\n{body}\n", encoding="utf-8", newline="\n")
        return path
