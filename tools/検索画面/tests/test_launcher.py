"""ダブルクリック用の run.bat の契約: 日本語は goto :main で飛び越えるコメントの中にだけ書く。

cmd.exe は bat をコンソールのコードページで読むので、実行される行に UTF-8 の日本語があると、
行が途中で切れて、コメントの切れ端がコマンドとして実行される。goto で飛び越えた行は解釈されない。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RUN_BAT = Path(__file__).resolve().parents[1] / "run.bat"
UTF8_BOM = b"\xef\xbb\xbf"
SKIP = b"goto :main"
LABEL = b":main"


def lines() -> list[bytes]:
    return RUN_BAT.read_bytes().split(b"\r\n")


def test_run_bat_is_utf8_without_bom_and_with_crlf():
    body = RUN_BAT.read_bytes()
    body.decode("utf-8")
    assert not body.startswith(UTF8_BOM)  # BOM があると、cmd.exe は1行目の @echo off を読めない。
    assert body.count(b"\r\n") == body.count(b"\n") > 0


def test_japanese_appears_only_in_the_skipped_comment():
    body = lines()
    assert body[:2] == [b"@echo off", SKIP]
    label_at = body.index(LABEL)
    outside = body[:2] + body[label_at:]
    assert [line for line in outside if not line.isascii()] == []
    assert any(not line.isascii() for line in body[2:label_at])


@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe が要る")
def test_cmd_skips_the_comment_without_running_any_of_it(tmp_path: Path):
    body = lines()
    header = body[: body.index(LABEL) + 1]
    probe = tmp_path / "probe.bat"
    probe.write_bytes(b"\r\n".join([*header, b"echo REACHED", b"exit /b 0", b""]))
    done = subprocess.run(["cmd", "/c", f"chcp 932 >nul 2>&1 & {probe}"], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
    assert (done.stdout + done.stderr).strip() == b"REACHED"
