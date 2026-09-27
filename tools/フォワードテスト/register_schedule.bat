@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - フォワードテストを毎朝自動で動かすよう、Windows のタスク スケジューラに登録する。
rem
rem    register_schedule.bat            : 2つのタスクを登録する（同じ名前があれば上書き）。
rem    register_schedule.bat /delete    : 2つのタスクを消す（フォワードテストを終えるとき）。
rem
rem  登録するタスク（毎日。開催の無い日は、すぐ終わる）:
rem    keiba-realtime-follow  毎朝 8:00  ..\..\..\jvdata-store\realtime_follow.bat
rem                           （開催日の間、各レースの発走の12分前にオッズ・馬体重を取り直す）
rem    keiba-forward-test     毎朝 8:30  このフォルダの run.bat
rem                           （発走の約10分前に予想して記録し、最後に精算する）
rem  毎日にしているのは、月曜の祝日の開催も拾うため。
rem  PC の電源が入っていて、この利用者がログオンしている間だけ動く（JV-Link が利用者の画面で動くため）。
rem  1回登録すれば、あとは何もしなくてよい。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - フォルダ名に日本語が入るので、パスは %~dp0 からだけ作る。
rem ===========================================================================
:main

set "STORE_BAT=%~dp0..\..\..\jvdata-store\realtime_follow.bat"
set "FORWARD_BAT=%~dp0run.bat"

if /i "%~1"=="/delete" goto :delete

if not exist "%STORE_BAT%" (
    echo [ERROR] jvdata-store realtime_follow.bat was not found: "%STORE_BAT%"
    echo         Merge jvdata-store PR "feat/realtime-follow" first.
    exit /b 1
)

schtasks /Create /F /TN "keiba-realtime-follow" /SC DAILY /ST 08:00 /TR "\"%STORE_BAT%\""
if errorlevel 1 exit /b 1
schtasks /Create /F /TN "keiba-forward-test" /SC DAILY /ST 08:30 /TR "\"%FORWARD_BAT%\""
if errorlevel 1 exit /b 1
echo Registered: keiba-realtime-follow (08:00), keiba-forward-test (08:30)
exit /b 0

:delete
schtasks /Delete /F /TN "keiba-realtime-follow"
schtasks /Delete /F /TN "keiba-forward-test"
exit /b 0
