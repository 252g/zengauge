#!/bin/bash
# ダブルクリックで ZEN Study にログインし、iPhone に送る QR コードを表示する。ログインし直すときも、これをもう一度開く。
cd "$(dirname "$0")" || exit 1

finish() {
  echo
  read -r -n 1 -p "何かキーを押すと閉じます。"
  exit "$1"
}

echo "=== zengauge の準備 ==="
echo

# Python 3.9 以上を探す（macOS 標準の python3 は 3.9 なのでそれも使える）。
PY=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Python が見つかりませんでした。"
  echo "「コマンドライン・デベロッパ・ツール」のインストールを求める画面が出たら「インストール」を押し、"
  echo "終わってから、もう一度このファイルをダブルクリックしてください。"
  echo "画面が出ないときは https://www.python.org/downloads/ から Python を入れてください。"
  finish 1
fi

echo "1/3 準備用のフォルダを作っています…"
if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv || { echo "作れませんでした。"; finish 1; }
fi

echo "2/3 必要なものを入れています…"
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt ||
  { echo "入れられませんでした。ネットにつながっているか確かめてください。"; finish 1; }

echo "3/3 ZEN Study にログインします。開いたブラウザでログインしてください。"
.venv/bin/python zengauge.py login || finish 1

echo
echo "ブラウザに出た QR コードを、iPhone のカメラで読み取ってください。"
echo "iPhone に「ログインできました」と出たら完了です。この画面とブラウザは閉じて大丈夫です。"
finish 0
