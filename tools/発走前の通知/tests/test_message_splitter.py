"""MessageSplitter（投稿の上限で分ける）のテスト。"""

from __future__ import annotations

from 発走前の通知.message_splitter import MessageSplitter


def test_短い文はそのまま() -> None:
    assert MessageSplitter(25).split("あ\nい") == ["あ\nい"]


def test_行の切れ目で上限以下に分ける() -> None:
    lines = [letter * 10 for letter in "abcde"]
    assert MessageSplitter(25).split("\n".join(lines)) == ["a" * 10 + "\n" + "b" * 10, "c" * 10 + "\n" + "d" * 10, "e" * 10]


def test_上限より長い行は上限で切る() -> None:
    assert MessageSplitter(10).split("x" * 25) == ["x" * 10, "x" * 10, "x" * 5]


def test_空の行は残り空の文は分けない() -> None:
    assert MessageSplitter(10).split("a\n\nb") == ["a\n\nb"]
    assert MessageSplitter(10).split("") == []
