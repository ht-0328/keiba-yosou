@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 発走前の通知を、毎日自動で動かすタスクを登録する（中央と地方の2つ）。
rem
rem    ダブルクリック                  : 次の2つのタスクを登録する（あれば置き換える）。
rem                                      「keiba-yosou-race-notify」      毎日 08:30 に run.bat --task（中央）
rem                                      「keiba-yosou-race-notify-local」毎日 08:35 に run.bat --task --local（地方）
rem    register_task.bat 08:00 08:05  : 時刻を変える（1つ目が中央、2つ目が地方）。
rem
rem  地方を 5 分ずらすのは、2つの run.bat が同時に uv sync を始めないようにするため。
rem  開催の無い日は、レースが無いことを確かめてすぐ終わる。PC が登録した時刻に起きていなければ、
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
set "AT_LOCAL=%~2"
if "%AT_LOCAL%"=="" set "AT_LOCAL=08:35"
set "RUN=%~dp0run.bat"
set "DIR=%~dp0"

call :register keiba-yosou-race-notify "--task" %AT%
if errorlevel 1 goto :failed
call :register keiba-yosou-race-notify-local "--task --local" %AT_LOCAL%
if errorlevel 1 goto :failed
pause
exit /b 0

:register
set "TASK=%~1"
set "TASK_ARGS=%~2"
set "TASK_AT=%~3"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$action = New-ScheduledTaskAction -Execute \"$env:RUN\" -Argument $env:TASK_ARGS -WorkingDirectory \"$env:DIR\";" ^
  "$trigger = New-ScheduledTaskTrigger -Daily -At $env:TASK_AT;" ^
  "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 14) -MultipleInstances IgnoreNew;" ^
  "Register-ScheduledTask -TaskName $env:TASK -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null;" ^
  "Write-Host ('Registered: ' + $env:TASK + ' (daily at ' + $env:TASK_AT + ', run.bat ' + $env:TASK_ARGS + ')')"
exit /b %errorlevel%

:failed
echo.
echo [ERROR] Could not register the task.
pause
exit /b 1
