@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 検索画面（ブラウザ）をダブルクリックで起動する。
rem
rem    ダブルクリック      : サーバーを起動して、ブラウザで開く。
rem    run.bat --port 9000 : 後ろに付けた引数は、そのまま web.py に渡る。
rem
rem  uv が要る。uv が PATH に無ければ、WinGet が入れる場所を探す。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem      cmd.exe は bat をコンソールのコードページ（日本語 Windows では 932）で読む。
rem      実行される行に UTF-8 の日本語があると、行が途中で切れて、
rem      コメントの切れ端がコマンドとして実行されてしまう。
rem      goto で飛び越えた行は解釈されないので、ここには日本語を書ける。
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
"%UV%" run --project "%PROJECT%" python web.py --open %*
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
pause
exit /b 1
