@echo off
chcp 65001 >nul
rem ダブルクリックで ZEN Study にログインし、iPhone に送る QR コードを表示する。ログインし直すときも、これをもう一度開く。
cd /d "%~dp0"
echo === zengauge の準備 ===
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python が見つかりませんでした。
  echo 開いたページから Python を入れてください。インストールの最初の画面で
  echo 「Add python.exe to PATH」にチェックを入れてから、もう一度このファイルをダブルクリックしてください。
  start "" https://www.python.org/downloads/
  goto fail
)

echo 1/3 準備用のフォルダを作っています…
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv || goto fail
)

echo 2/3 必要なものを入れています…
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto fail

echo 3/3 ZEN Study にログインします。開いたブラウザでログインしてください。
".venv\Scripts\python.exe" zengauge.py login || goto fail

echo.
echo ブラウザに出た QR コードを、iPhone のカメラで読み取ってください。
echo iPhone に「ログインできました」と出たら完了です。この画面とブラウザは閉じて大丈夫です。
pause
exit /b 0

:fail
echo.
echo うまくいきませんでした。上のメッセージを確かめてください。
pause
exit /b 1
