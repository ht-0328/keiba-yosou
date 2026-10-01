"""``uv run python -m yosou.custom_binary features`` / ``train`` / ``predict`` / ``evaluate`` の入口。使い方は ``docs/custom_binary.md``。"""

from .command import CommandLine

if __name__ == "__main__":
    CommandLine().run()
