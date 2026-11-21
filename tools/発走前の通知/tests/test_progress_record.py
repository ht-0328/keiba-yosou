"""ProgressRecord（進み具合をファイルにも残す）のテスト。"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from 発走前の通知.progress_record import ProgressRecord


def _now() -> datetime:
    return datetime(2025, 4, 19, 8, 35, 1)


def test_画面にそのまま流し_ファイルには行の頭に時刻を付けて足す(tmp_path: Path) -> None:
    screen = io.StringIO()
    path = tmp_path / "logs" / "進み具合.log"
    record = ProgressRecord(screen, path, now=_now)
    record.write("速報の取り込み")
    record.write("が終わりました\n")
    record.write("次の行\n")
    assert screen.getvalue() == "速報の取り込みが終わりました\n次の行\n"
    assert path.read_text(encoding="utf-8") == "08:35:01 速報の取り込みが終わりました\n08:35:01 次の行\n"


def test_ファイルに書けなくても画面には流す(tmp_path: Path) -> None:
    screen = io.StringIO()
    blocked = tmp_path / "ファイル"
    blocked.write_text("x", encoding="utf-8")
    record = ProgressRecord(screen, blocked / "進み具合.log", now=_now)
    record.write("続けます\n")
    assert screen.getvalue() == "続けます\n"
