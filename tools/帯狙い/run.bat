@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 帯狙い（払戻 100万円以上を狙う参考の買い目）を出して開く（ダブルクリック用）。
rem
rem    ダブルクリック                 : 今日以降の開催日ごとに、荒れそうなレースを1つ選び、
rem                                     荒れる前提の予想で1レース1万円の3連単の買い目を出して、
rem                                     結果の表（reports の 帯狙い/最新.md）を既定のアプリで開く。
rem    run.bat --date 2026-10-18      : 後ろに付けた引数は obi.py に渡る
rem                                     （--date でその日だけ、--plan で買い方を替える）。
rem
rem  買い目は参考（研究「百万馬券を当てる」の確かめで、どの買い方も採用の基準に
rem  届かなかった）。財布にも買い目の記録にも書かない。
rem  先に jvdata-store で、出馬表と速報（オッズ）を取り込む。組ごとのオッズは当日の
rem  速報にしか無いので、買い目は当日に実行したときだけ組まれる。
rem  1日に数分かかる。
rem
rem  uv が要る。uv が PATH に無ければ、WinGet が入れる場所を探す。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem      cmd.exe は bat をコンソールのコードページ（日本語 Windows では 932）で読むので、
rem      実行される行に UTF-8 の日本語があると、行が途中で切れて誤動作する。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - フォルダ名に日本語が入るので、パスは %~dp0 からだけ作る。
rem      結果のファイルの名前も日本語なので、開くのは obi.py の --open に任せる。
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
"%UV%" run --project "%PROJECT%" python obi.py --open %*
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
pause
exit /b 1
