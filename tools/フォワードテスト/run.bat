@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - フォワードテストを、開催日の間ずっと動かす。
rem
rem    run.bat                       : 今日の開催日を追う（最後のレースの精算まで動き続ける）。
rem    run.bat --date 2026-10-03     : 後ろに付けた引数は follow.py に渡る。
rem
rem  各レースの発走の約10分前に、当日の予想と同じモデル・同じ線で予想し、
rem  期待値 1.2 以上の複勝を1点100円で「買ったつもり」として記録する。実際のお金は使わない。
rem  最後のレースの発走から40分たったら精算して、reports\フォワードテスト\成績.md を書き直す。
rem  オッズは jvdata-store の realtime_follow.bat が発走の12分前に取り直す。先にそちらを動かしておく。
rem  ふだんは Windows のタスク スケジューラが毎朝呼ぶ（登録は register_schedule.bat）。
rem  人が見ていなくても動くように、終わっても pause しない。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem      cmd.exe は bat をコンソールのコードページ（日本語 Windows では 932）で読むので、
rem      実行される行に UTF-8 の日本語があると、行が途中で切れて誤動作する。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - フォルダ名に日本語が入るので、パスは %~dp0 からだけ作る。
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
exit /b 1

:run
"%UV%" sync --quiet --project "%PROJECT%"
if errorlevel 1 exit /b 1

set PYTHONIOENCODING=utf-8
"%UV%" run --project "%PROJECT%" python follow.py %*
exit /b %errorlevel%
