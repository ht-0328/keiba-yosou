@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 発走前の通知の毎日のタスクを解除する
rem  （中央の keiba-yosou-race-notify と、地方の keiba-yosou-race-notify-local）。
rem  登録されていない方は「見つかりません」と出るだけで、もう片方は解除する。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem ===========================================================================
:main

schtasks /Delete /TN keiba-yosou-race-notify /F
schtasks /Delete /TN keiba-yosou-race-notify-local /F
pause
exit /b 0
