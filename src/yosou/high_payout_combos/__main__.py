"""``uv run python -m yosou.high_payout_combos tables`` / ``walk`` / ``train`` の入口。使い方は ``command/command_line.py``。"""

from __future__ import annotations

from .command import CommandLine

if __name__ == "__main__":
    CommandLine().run()
