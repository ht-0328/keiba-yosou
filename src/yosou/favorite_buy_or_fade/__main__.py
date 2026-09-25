"""``uv run python -m yosou.favorite_buy_or_fade train`` / ``evaluate`` / ``predict`` の入口。使い方は ``command/command_line.py``。"""

from __future__ import annotations

from .command import CommandLine

if __name__ == "__main__":
    CommandLine().run()
