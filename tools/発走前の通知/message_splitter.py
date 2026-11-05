"""長い文を、Discord の1つの投稿の上限に収まる塊に、行の切れ目で分ける。"""

from __future__ import annotations

#: Discord の1つの投稿に書ける文字数の上限。
DISCORD_LIMIT = 2000


class MessageSplitter:
    def __init__(self, limit: int = DISCORD_LIMIT) -> None:
        self._limit = limit

    def split(self, text: str) -> list[str]:
        """上限以下の塊に分ける。行の途中では切らない（1行が上限より長いときだけ、その行を上限で切る）。"""
        chunks: list[str] = []
        current = ""
        for line in self._fitted_lines(text):
            if current and len(current) + 1 + len(line) > self._limit:
                chunks.append(current)
                current = line
                continue
            current = f"{current}\n{line}" if current else line
        return [*chunks, current] if current else chunks

    def _fitted_lines(self, text: str) -> list[str]:
        """行ごとに。上限より長い行は上限ごとに切る。"""
        return [line[start:start + self._limit] for line in text.splitlines() for start in range(0, max(len(line), 1), self._limit)]
