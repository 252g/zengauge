#!/bin/bash
# ダブルクリックで、30分ごとの自動更新をやめる。
cd "$(dirname "$0")" || exit 1
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" zengauge.py schedule --off
echo
read -r -n 1 -p "何かキーを押すと閉じます。"
