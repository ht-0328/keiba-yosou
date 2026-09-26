@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 当日の予想をダブルクリックで出す。
rem
rem    ダブルクリック                 : 今日の、今より後に発走するレースを予想する。
rem    run.bat --after 00:00          : 後ろに付けた引数は predict_today.py に渡る
rem                                     （今日の全レース・--date で別の日・--line で線を変える）。
rem
rem  先に jvdata-store の realtime_today.bat で、その日の速報（馬体重・全券種のオッズ）を取り込む。
rem  買い（複勝・期待値 1.2 以上）の一覧と、レースごとの期待値の上位5頭を出し、
rem  reports\当日の予想\ にも書く。はじめて使うときは、モデルの学習に数分かかる。
rem  オッズは締め切りまで動くので、発走の10〜15分前に 取り込み → 予想 をやり直す。
rem
rem  uv が要る。uv が PATH に無ければ、WinGet が入れる場所を探す。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem      cmd.exe は bat をコンソールのコードページ（日本語 Windows では 932）で読むので、
rem      実行される行に UTF-8 の日本語があると、行が途中で切れて誤動作する。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - フォルダ名に日本語が入るので、パスは %~dp0 からだけ作る。
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
"%UV%" run --project "%PROJECT%" python predict_today.py %*
if errorlevel 1 goto :failed
echo.
pause
exit /b 0

:failed
echo.
pause
exit /b 1
