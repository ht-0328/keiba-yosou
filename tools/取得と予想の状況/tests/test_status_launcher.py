"""ダブルクリック用の run.bat の契約と、画面を「状況」のタブで開くアドレス、モデルの置き場所の名前のテスト。

cmd.exe は bat をコンソールのコードページで読むので、実行される行に UTF-8 の日本語があると、
行が途中で切れて、コメントの切れ端がコマンドとして実行される。goto で飛び越えた行は解釈されない。
"""

from __future__ import annotations

from pathlib import Path

from 検索画面 import server
from 今週の予想 import model_folders

FOLDER = Path(__file__).resolve().parents[1]
RUN_BAT = FOLDER / "run.bat"


def test_run_bat_is_utf8_without_bom_and_with_crlf() -> None:
    body = RUN_BAT.read_bytes()
    body.decode("utf-8")
    assert not body.startswith(b"\xef\xbb\xbf")  # BOM があると、cmd.exe は1行目の @echo off を読めない
    assert body.count(b"\r\n") == body.count(b"\n") > 0


def test_run_bat_has_japanese_only_in_the_skipped_comment() -> None:
    lines = RUN_BAT.read_bytes().split(b"\r\n")
    assert lines[:2] == [b"@echo off", b"goto :main"]
    label_at = lines.index(b":main")
    assert [line for line in lines[:2] + lines[label_at:] if not line.isascii()] == []
    assert b"python view.py" in RUN_BAT.read_bytes()


def test_page_url_opens_the_overview_tab() -> None:
    assert server.page_url(8767, "overview") == "http://127.0.0.1:8767/#/overview"


def test_model_folder_names_match_each_yosou() -> None:
    """モデルの置き場所の予想の名前は、重い import を避けて書き写してあるので、元と同じことを確かめる。"""
    from yosou.favorites_out_of_top3.command.yosou_name import YOSOU_NAME as FAVORITE
    from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME as FORM

    assert model_folders.FORM_YOSOU_NAME == FORM and model_folders.FAVORITE_YOSOU_NAME == FAVORITE
    assert [name for name, _ in model_folders.MODEL_ROOTS] == [FORM, FAVORITE]
