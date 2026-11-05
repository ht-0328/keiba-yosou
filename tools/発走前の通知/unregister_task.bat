@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 発走前の通知の毎日のタスク（keiba-yosou-race-notify）を解除する。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem ===========================================================================
:main

schtasks /Delete /TN keiba-yosou-race-notify /F
pause
exit /b %errorlevel%
