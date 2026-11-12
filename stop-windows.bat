@echo off
chcp 65001 >nul
rem ダブルクリックで、30分ごとの自動更新をやめる。
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" zengauge.py schedule --off
) else (
  py -3 zengauge.py schedule --off
)
pause
