"""ダブルクリック用の run.bat の契約のテスト。

cmd.exe は bat をコンソールのコードページで読むので、実行される行に UTF-8 の日本語があると、
行が途中で切れて、コメントの切れ端がコマンドとして実行される。goto で飛び越えた行は解釈されない。
"""

from __future__ import annotations

from pathlib import Path

BAT = Path(__file__).resolve().parents[1] / "run.bat"


def test_bat_is_utf8_without_bom_and_with_crlf() -> None:
    body = BAT.read_bytes()
    body.decode("utf-8")
    assert not body.startswith(b"\xef\xbb\xbf")  # BOM があると、cmd.exe は1行目の @echo off を読めない
    assert body.count(b"\r\n") == body.count(b"\n") > 0


def test_bat_has_japanese_only_in_the_skipped_comment() -> None:
    lines = BAT.read_bytes().split(b"\r\n")
    assert lines[:2] == [b"@echo off", b"goto :main"]
    label_at = lines.index(b":main")
    assert [line for line in lines[:2] + lines[label_at:] if not line.isascii()] == []


def test_run_bat_makes_the_obi_tickets_and_opens_the_page() -> None:
    text = BAT.read_bytes().decode("utf-8")
    assert "python obi.py --open %*" in text
