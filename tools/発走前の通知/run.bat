@echo off
goto :main
rem ===========================================================================
rem  keiba-yosou - 発走前の通知（ダブルクリック用）。
rem
rem    ダブルクリック                  : 今日の開催を、朝の準備（出馬表・速報の取り込み・
rem                                      全レースの予想）のあと、発走10分前ごとに予想して
rem                                      Discord に投稿する。最後のレースまで黒い窓が残る。
rem    run.bat --rid 2026110105041101  : 後ろに付けた引数は notify.py に渡る
rem                                      （--date でその日、--rid でそのレースだけ今すぐ、
rem                                      --test でつながりの確認、--dry-run で投稿せず画面に）。
rem    run.bat --task                  : タスクスケジューラから動かす形（終わっても止まらない）。
rem    run.bat --task --local          : 同じ形で地方競馬。--task の後ろの引数は notify.py に渡る。
rem                                      register_task.bat がこの2つの形で登録する。
rem
rem  ウェブフック URL は reports\発走前の通知\設定.json に置く（Git には入れない）。
rem  取り込みは隣の jvdata-store（jvstore）、予想は tools\今週の予想\forecast.py を呼ぶ。
rem  検索画面や jvdata-store の画面が DB を開いていると取り込みが失敗するので、動かす間は閉じておく。
rem
rem  uv が要る。uv が PATH に無ければ、WinGet が入れる場所を探す。
rem
rem  このファイルの決まり:
rem    - 日本語は、上の goto :main と下の :main の間（このコメントの中）にだけ書く。
rem      cmd.exe は bat をコンソールのコードページ（日本語 Windows では 932）で読むので、
rem      実行される行に UTF-8 の日本語があると、行が途中で切れて誤動作する。
rem    - 文字コードは UTF-8（BOM なし）、改行は CRLF で保存する。
rem    - フォルダ名に日本語が入るので、パスは %~dp0 からだけ作る。
rem    - %* は shift しても変わらないので、--task のときは後ろの引数を1つずつ集め直して渡す。
rem ===========================================================================
:main

cd /d "%~dp0"
set "PROJECT=%~dp0..\.."
set "ARGS=%*"
set "NOPAUSE="
if not "%~1"=="--task" goto :args_done
set "NOPAUSE=1"
set "ARGS="
shift
:collect_args
if "%~1"=="" goto :args_done
set "ARGS=%ARGS% %1"
shift
goto :collect_args
:args_done

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
"%UV%" run --project "%PROJECT%" python notify.py %ARGS%
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
if not defined NOPAUSE pause
exit /b 1
