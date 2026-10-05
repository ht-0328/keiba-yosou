@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 取得と予想の状況を画面で開く（ダブルクリック用）。
rem
rem    ダブルクリック       : 検索画面を起動して、「状況」のタブをブラウザで開く
rem                           （起動済みなら開くだけ）。
rem    run.bat --port 9000  : 後ろに付けた引数は view.py に渡る。
rem
rem  「状況」のタブは、中央（jvdata-store）と地方（nvdata-store）のデータがどこまで入っているか
rem  （出馬表・オッズ・馬体重・確定成績・同期の記録）と、今週の予想（中央）がそれに追いついているかを、
rem  開催日ごと・レースごとに見せる。取得の画面が動いているか・何を取得中かも出す。30秒ごとに自動で更新する。
rem  同じ中身を表で出すだけなら、同じフォルダの status.py。画面を閉じるには、この黒い窓を閉じる。
rem
rem  uv が要る。uv が PATH に無ければ、WinGet が入れる場所を探す。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem      cmd.exe は bat をコンソールのコードページ（日本語 Windows では 932）で読むので、
rem      実行される行に UTF-8 の日本語があると、行が途中で切れて誤動作する。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - フォルダ名に日本語が入るので、パスは %~dp0 からだけ作る。
rem      検索画面のフォルダも日本語なので、画面は同じフォルダの view.py から起動する。
rem    - if ( ... ) の塊の中の %VAR% は、塊を実行する前に展開されてしまう。
rem      そのため、下の uv 探しは塊を使わずに書いている。
rem ===========================================================================
:main

cd /d "%~dp0"
set "PROJECT=%~dp0..\.."

where uv >nul 2>&1
if not errorlevel 1 set "UV=uv"
if not errorlevel 1 goto :run

set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe"
if exist "%UV%" goto :run

echo [ERROR] uv was not found. Install uv or put it on PATH.
echo         Looked for: %UV%
goto :failed

:run
"%UV%" sync --quiet --project "%PROJECT%"
if errorlevel 1 (
    echo [ERROR] "uv sync" failed.
    goto :failed
)

set PYTHONIOENCODING=utf-8
"%UV%" run --project "%PROJECT%" python view.py %*
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
pause
exit /b 1
