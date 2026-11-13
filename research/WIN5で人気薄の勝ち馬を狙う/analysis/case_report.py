"""事例の報告: 見出しと前書きを付けて、表を1つの Markdown に並べて書く。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from 共通 import render
from 共通.render import Table


@dataclass(frozen=True)
class CaseReport:
    """``out_dir`` に ``<name>.md`` を書き、書いた場所を返す。改行は LF。"""

    out_dir: Path

    def write(self, name: str, heading: str, intro: str, sections: list[tuple[str, list[Table]]]) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"{name}.md"
        parts = [f"# {heading}", intro]
        for section, tables in sections:
            parts.append(f"## {section}")
            parts.extend(render.to_markdown(table) for table in tables)
        path.write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
        return path
