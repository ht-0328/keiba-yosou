@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 今週の予想を作って、画面で開く（ダブルクリック用）。
rem
rem    ダブルクリック                 : 今日以降の全レースを予想してから
rem                                     （同じ時点で作ってあるレースは飛ばす）、
rem                                     検索画面の「今週の予想」のタブをブラウザで開く。
rem    run.bat --date 2026-10-04      : 後ろに付けた引数は forecast.py に渡る
rem                                     （--date でその日だけ、--venue で競馬場だけ）。
rem
rem  予想を作らずに画面だけ開くなら、同じフォルダの view.bat。
rem  先に jvdata-store で、今週の出馬表（jvstore sync）と速報
rem  （jvstore realtime --date 開催日。オッズと馬体重）を取り込む。
rem  1レースに1分ほどかかる（はじめての週は全部で30〜50分）。オッズや馬体重を
rem  取り込み直したら、もう一度実行する（時点が変わったレースだけ予想し直す）。
rem  予想できないレースがあっても、画面は開く。画面を閉じるには、この黒い窓を閉じる。
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
"%UV%" run --project "%PROJECT%" python forecast.py --skip-saved %*
if errorlevel 1 echo [WARN] forecast.py failed. Opening the screen anyway.
"%UV%" run --project "%PROJECT%" python view.py
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
pause
exit /b 1
