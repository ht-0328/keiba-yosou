@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 発走前の通知を、毎日 8:30 に自動で動かすタスクを登録する。
rem
rem    ダブルクリック            : 毎日 08:30 に run.bat --task を動かすタスク
rem                                「keiba-yosou-race-notify」を登録する（あれば置き換える）。
rem    register_task.bat 08:00  : 時刻を変える。
rem
rem  開催の無い日は、レースが無いことを確かめてすぐ終わる。PC が 8:30 に起きていなければ、
rem  次に起きたときに動く。電池で動いていても始めて、止めない。1回の上限は 14 時間。
rem  利用者がログインしている間だけ動く（黒い窓が出て、進み具合が見える）。
rem  解除は unregister_task.bat。登録の中身は「タスク スケジューラ」でも見られる。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - 日本語のパスは %~dp0 から環境変数に入れて PowerShell に渡す。
rem ===========================================================================
:main

cd /d "%~dp0"
set "AT=%~1"
if "%AT%"=="" set "AT=08:30"
set "TASK=keiba-yosou-race-notify"
set "RUN=%~dp0run.bat"
set "DIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$action = New-ScheduledTaskAction -Execute \"$env:RUN\" -Argument '--task' -WorkingDirectory \"$env:DIR\";" ^
  "$trigger = New-ScheduledTaskTrigger -Daily -At $env:AT;" ^
  "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 14) -MultipleInstances IgnoreNew;" ^
  "Register-ScheduledTask -TaskName $env:TASK -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null;" ^
  "Write-Host ('Registered: ' + $env:TASK + ' (daily at ' + $env:AT + ')')"
if errorlevel 1 goto :failed
pause
exit /b 0

:failed
echo.
echo [ERROR] Could not register the task.
pause
exit /b 1
