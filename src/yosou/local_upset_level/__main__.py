"""``uv run python -m yosou.local_upset_level train`` / ``predict`` の入口。使い方は ``command/command_line.py``。"""

from __future__ import annotations

from .command import CommandLine

if __name__ == "__main__":
    CommandLine().run()
