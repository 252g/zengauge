"""zengauge: ZEN Study のレポート進捗を PC で取得し、iPhone の Scriptable ウィジェットへ渡す。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import api, config, paths, schedule, session, sync


def ensure_browser() -> None:
    """Download Playwright's Chromium on first use (a no-op once it is there)."""
    print("ログイン用のブラウザを準備しています（初回は数分かかります）…", flush=True)
    result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    if result.returncode != 0:
        raise SystemExit("ブラウザを準備できませんでした。ネットにつながっているか確かめて、もう一度試してください。")


def cmd_login(args: argparse.Namespace) -> int:
    ensure_browser()
    path = session.login(args.timeout)
    print(f"ログイン情報を保存しました: {path}")
    return cmd_sync(argparse.Namespace(quiet=False, output=None))


def cmd_import(args: argparse.Namespace) -> int:
    source = Path(args.path).expanduser()
    text = source.read_text(encoding="utf-8").strip()
    path = session.import_storage_state(source) if text.startswith("{") else session.import_cookie_header(text)
    print(f"ログイン情報を取り込みました: {path}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    status, path = sync.run(Path(args.output).expanduser() if args.output else None)
    messages = {"ok": "進捗を更新しました", "login_required": "ログインが必要です（setup をダブルクリックしてログインしてください）",
                "error": "進捗を取得できませんでした"}
    if not args.quiet or status != "ok":
        print(messages[status] + (f": {path}" if path else "（Scriptable の iCloud フォルダが見つかりません。`setup --scriptable-dir` で指定してください）"))
    return 0 if status == "ok" and path else 1


def cmd_status(_: argparse.Namespace) -> int:
    settings = config.load()
    folder = paths.find_scriptable_dir(settings.get("scriptable_dir"))
    print(f"ログイン情報: {paths.storage_state_path()}" + ("" if paths.storage_state_path().exists() else "（未保存）"))
    try:
        valid = api.session_is_valid(session.cookie_header(session.load_cookies()))
        print("ログイン: " + ("有効" if valid else "切れています"))
    except session.LoginRequired as error:
        print(f"ログイン: {error}")
    print(f"Scriptable フォルダ: {folder or '見つかりません'}")
    data = sync.latest(folder) if folder else None
    if data:
        c = data.get("current") or {}
        print(f"最後の書き出し: {data.get('fetchedAt', '-')} / {c.get('month', '-')}月 "
              f"{c.get('chaptersPassed', '-')}/{c.get('chaptersTotal', '-')} / 状態 {data.get('status')}")
    print("自動更新: " + ("登録済み" if schedule.installed() else "未登録"))
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    settings = config.load()
    if args.scriptable_dir is not None:
        if args.scriptable_dir and not Path(args.scriptable_dir).expanduser().is_dir():
            print("そのフォルダは見つかりません。")
            return 1
        settings["scriptable_dir"] = args.scriptable_dir or None
        config.save(settings)
    print(f"Scriptable フォルダ: {paths.find_scriptable_dir(settings.get('scriptable_dir')) or '見つかりません'}")
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    print(schedule.uninstall() if args.off else schedule.install(args.minutes))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zengauge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="ブラウザで ZEN Study にログインして保存する")
    p.add_argument("--timeout", type=int, default=10, help="ログインを待つ分数")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("import", help="既存のログイン情報を取り込む（storageState.json か Cookie ヘッダのファイル）")
    p.add_argument("path")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("sync", help="進捗を取得して Scriptable の iCloud フォルダへ書き出す")
    p.add_argument("--output", help="書き出し先フォルダ（省略時は自動検出）")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("status", help="ログインと書き出し先の状態を表示する")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("setup", help="Scriptable の iCloud フォルダを指定する")
    p.add_argument("--scriptable-dir", help="フォルダのパス（空文字で自動検出に戻す）")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("schedule", help="自動更新を登録・解除する")
    p.add_argument("--minutes", type=int, default=30)
    p.add_argument("--off", action="store_true", help="解除する")
    p.set_defaults(func=cmd_schedule)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except session.LoginRequired as error:
        print(error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
