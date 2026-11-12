"""Hand the saved login to the iPhone widget as a QR code.

The QR code holds a scriptable:// link. Scanning it with the iPhone camera opens the
widget script in Scriptable, which checks the login and stores it in its keychain.
After that the widget fetches progress by itself, so the PC is no longer needed.
"""
from __future__ import annotations

import html
import os
import webbrowser
from pathlib import Path
from urllib.parse import quote

from . import paths

SCRIPT_NAME = "ZEN Study進捗"


def import_url(cookie: str, script_name: str = SCRIPT_NAME) -> str:
    return f"scriptable:///run/{quote(script_name, safe='')}?action=import&cookie={quote(cookie, safe='')}"


def svg(data: str) -> str:
    try:
        import qrcode
        import qrcode.image.svg
    except ModuleNotFoundError as error:
        raise SystemExit("qrcode が入っていません。setup をダブルクリックしてやり直してください。") from error
    image = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    return image.to_string(encoding="unicode")


PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>zengauge: iPhone に送る</title>
<style>
 body {{ font: 16px -apple-system, "Segoe UI", sans-serif; text-align: center; margin: 32px 16px; color: #1c1c1e; background: #fff; }}
 .qr {{ display: inline-block; padding: 16px; background: #fff; border-radius: 16px; box-shadow: 0 2px 16px #0002; }}
 .qr svg {{ width: min(320px, 80vw); height: auto; display: block; }}
 ol {{ display: inline-block; text-align: left; line-height: 1.8; }}
 .warn {{ color: #c0392b; font-size: 14px; }}
</style>
<h1>iPhone のカメラで読み取ってください</h1>
<div class="qr">{svg}</div>
<ol>
 <li>iPhone で Scriptable に「{script}」を入れておく</li>
 <li>カメラアプリをこの QR コードに向け、出てきた「Scriptable で開く」を押す</li>
 <li>「保存する」を押して「ログインできました」と出たら完了（このページは閉じてよい）</li>
</ol>
<p class="warn">この QR コードには ZEN Study のログイン情報が入っています。人に見せたり、撮影して送ったりしないでください。</p>
"""


def show(cookie: str) -> Path:
    """Write the QR page into the private data folder and open it in the default browser."""
    path = paths.data_dir() / "qr.html"
    path.write_text(PAGE.format(svg=svg(import_url(cookie)), script=html.escape(SCRIPT_NAME)), encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)
    webbrowser.open(path.resolve().as_uri())
    return path
