"""zengauge: PC で ZEN Study にログインし、QR コードで iPhone の Scriptable ウィジェットへ渡す。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import api, paths, qr, session, summary


def ensure_browser() -> None:
    """Download Playwright's Chromium on first use (a no-op once it is there)."""
    print("ログイン用のブラウザを準備しています（初回は数分かかります）…", flush=True)
    result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    if result.returncode != 0:
        raise SystemExit("ブラウザを準備できませんでした。ネットにつながっているか確かめて、もう一度試してください。")


def cmd_login(args: argparse.Namespace) -> int:
    ensure_browser()
    session.login(args.timeout)
    print("ログインできました。")
    return cmd_qr(args)


def cmd_qr(_: argparse.Namespace) -> int:
    cookie = session.cookie_header(session.load_cookies())
    if not api.session_is_valid(cookie):
        raise session.LoginRequired("ログインが切れています。setup をダブルクリックしてログインし直してください。")
    qr.show(cookie)
    print("ブラウザに QR コードを表示しました。iPhone のカメラで読み取ってください。")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    source = Path(args.path).expanduser()
    text = source.read_text(encoding="utf-8").strip()
    path = session.import_storage_state(source) if text.startswith("{") else session.import_cookie_header(text)
    print(f"ログイン情報を取り込みました: {path}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    path = paths.storage_state_path()
    print(f"ログイン情報: {path}" + ("" if path.exists() else "（未保存）"))
    try:
        cookies = session.load_cookies()
        cookie = session.cookie_header(cookies)
    except session.LoginRequired as error:
        print(f"ログイン: {error}")
        return 1
    if not api.session_is_valid(cookie):
        print("ログイン: 切れています")
        return 1
    expires = session.expires_at(cookies)
    print("ログイン: 有効" + (f"（{expires:%m/%d} ごろまで）" if expires else ""))
    data = summary.summarize(*_progress(cookie))
    c = data["current"]
    print(f"{c['month']}月レポート: {c['chaptersPassed']}/{c['chaptersTotal']}  年間: {data['year']['passed']}/{data['year']['total']}")
    return 0


def _progress(cookie: str) -> tuple[dict, dict | None, datetime]:
    now = datetime.now(timezone.utc)
    overview = api.overview(cookie)
    current = summary.pick_month(overview.get("monthly_summaries") or [], now)
    detail = None
    if current:
        try:
            detail = api.monthly(cookie, current["year"], current["month"], overview.get("service") or "basic")
        except api.ApiError:
            pass
    return overview, detail, now


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zengauge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="ブラウザで ZEN Study にログインし、iPhone に送る QR コードを表示する")
    p.add_argument("--timeout", type=int, default=10, help="ログインを待つ分数")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("qr", help="保存したログインの QR コードをもう一度表示する")
    p.set_defaults(func=cmd_qr)

    p = sub.add_parser("status", help="ログインの状態と今月の進捗を表示する")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("import", help="既存のログイン情報を取り込む（storageState.json か Cookie ヘッダのファイル）")
    p.add_argument("path")
    p.set_defaults(func=cmd_import)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except session.LoginRequired as error:
        print(error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
