"""設計書のフォルダの中で、文書どうしのリンクが実在するかを確かめる。

使い方: uv run --no-project python .claude/skills/designing-yosou-models/scripts/check_links.py "docs/design/<予想のやり方>"

確かめること:
- `[文字](NN-xxx.md)` のリンク先のファイルが、同じフォルダにあるか。
- `[文字](NN-xxx.md#節)` の「節」が、リンク先の見出しから GitHub と同じ規則で作った名前（slug）にあるか。

問題が無ければ「問題 0 件」と出して 0 で終わる。問題があれば1件ずつ出して 1 で終わる。
"""

import re
import sys
from pathlib import Path

# 同じフォルダの文書へのリンク。フォルダの外（../ など）や http のリンクは見ない。
LINK = re.compile(r"\]\(([^)/#:]+\.md)(?:#([^)]*))?\)")
HEADING = re.compile(r"^#+ (.+)$", re.MULTILINE)


def slug(heading: str) -> str:
    """見出しから、GitHub がリンクに使う名前を作る（小文字にし、記号を消し、空白を - にする）。"""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def check(folder: Path) -> list[str]:
    problems = []
    for doc in sorted(folder.glob("*.md")):
        for target, anchor in LINK.findall(doc.read_text(encoding="utf-8")):
            linked = folder / target
            if not linked.exists():
                problems.append(f"ファイルが無い: {doc.name} → {target}")
                continue
            if anchor:
                slugs = {slug(h) for h in HEADING.findall(linked.read_text(encoding="utf-8"))}
                if anchor not in slugs:
                    problems.append(f"節が無い: {doc.name} → {target}#{anchor}")
    return problems


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"フォルダが無い: {folder}")
        return 2
    problems = check(folder)
    for problem in problems:
        print(problem)
    print(f"問題 {len(problems)} 件")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
