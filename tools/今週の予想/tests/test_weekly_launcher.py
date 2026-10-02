"""ダブルクリック用の run.bat・view.bat の契約と、画面を「今週の予想」のタブで開くアドレスのテスト。

cmd.exe は bat をコンソールのコードページで読むので、実行される行に UTF-8 の日本語があると、
行が途中で切れて、コメントの切れ端がコマンドとして実行される。goto で飛び越えた行は解釈されない。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 検索画面 import server

FOLDER = Path(__file__).resolve().parents[1]
BATS = [FOLDER / "run.bat", FOLDER / "view.bat"]


@pytest.mark.parametrize("bat", BATS, ids=lambda path: path.name)
def test_bat_is_utf8_without_bom_and_with_crlf(bat: Path) -> None:
    body = bat.read_bytes()
    body.decode("utf-8")
    assert not body.startswith(b"\xef\xbb\xbf")  # BOM があると、cmd.exe は1行目の @echo off を読めない
    assert body.count(b"\r\n") == body.count(b"\n") > 0


@pytest.mark.parametrize("bat", BATS, ids=lambda path: path.name)
def test_bat_has_japanese_only_in_the_skipped_comment(bat: Path) -> None:
    lines = bat.read_bytes().split(b"\r\n")
    assert lines[:2] == [b"@echo off", b"goto :main"]
    label_at = lines.index(b":main")
    assert [line for line in lines[:2] + lines[label_at:] if not line.isascii()] == []


def test_run_bat_makes_forecasts_then_opens_the_screen() -> None:
    text = (FOLDER / "run.bat").read_bytes().decode("utf-8")
    assert text.index("python forecast.py --skip-saved") < text.index("python view.py")


def test_page_url_opens_the_forecast_tab() -> None:
    assert server.page_url(8767) == "http://127.0.0.1:8767/"
    assert server.page_url(8767, "forecast") == "http://127.0.0.1:8767/#/forecast"
