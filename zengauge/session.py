"""Saved ZEN Study login.

The login itself is done by hand in a Chromium window opened by Playwright.
Only the resulting nnn.ed.nico cookies are stored locally; the password never passes through here.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from . import api, paths

COOKIE_DOMAIN = "nnn.ed.nico"
LOGIN_URL = "https://www.nnn.ed.nico/login"


class LoginRequired(Exception):
    pass


def _write_private(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    if os.name != "nt":
        tmp.chmod(0o600)
    tmp.replace(path)


def load_cookies(path: Path | None = None) -> list[dict]:
    path = path or paths.storage_state_path()
    if not path.exists():
        raise LoginRequired("ログイン情報がありません。setup をダブルクリックしてログインしてください。")
    state = json.loads(path.read_text(encoding="utf-8"))
    return [c for c in state.get("cookies", []) if c.get("domain", "").lstrip(".").endswith(COOKIE_DOMAIN)]


def cookie_header(cookies: list[dict]) -> str:
    header = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    if "_zane_session=" not in header:
        raise LoginRequired("ログイン情報が古いか不完全です。setup をダブルクリックしてログインし直してください。")
    return header


def expires_at(cookies: list[dict]) -> "datetime | None":
    """When the session cookie expires, if the server gave it an expiry."""
    from datetime import datetime
    for c in cookies:
        if c.get("name") == "_zane_session" and (c.get("expires") or -1) > 0:
            return datetime.fromtimestamp(c["expires"])
    return None


def save_storage_state(state: dict, path: Path | None = None) -> Path:
    path = path or paths.storage_state_path()
    _write_private(path, json.dumps(state, ensure_ascii=False))
    return path


def import_cookie_header(header: str) -> Path:
    """Store a "name=value; name2=value2" cookie header (e.g. copied from a browser's developer tools)."""
    cookies = []
    for part in header.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name:
            cookies.append({"name": name, "value": value, "domain": ".nnn.ed.nico", "path": "/"})
    cookie_header(cookies)  # validates _zane_session is present
    return save_storage_state({"cookies": cookies, "origins": []})


def import_storage_state(source: Path) -> Path:
    state = json.loads(source.read_text(encoding="utf-8"))
    kept = [c for c in state.get("cookies", []) if c.get("domain", "").lstrip(".").endswith(COOKIE_DOMAIN)]
    cookie_header(kept)
    return save_storage_state({"cookies": kept, "origins": []})


async def _login_with_browser(timeout_minutes: int) -> Path:
    try:
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as error:
        raise SystemExit("Playwright が入っていません。setup をダブルクリックしてやり直してください。") from error

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        print("開いたブラウザで ZEN Study にログインしてください。ログインを確認したら自動で閉じます。", flush=True)
        deadline = asyncio.get_running_loop().time() + timeout_minutes * 60
        try:
            while asyncio.get_running_loop().time() < deadline:
                if not browser.is_connected() or page.is_closed():
                    raise SystemExit("ログイン前にブラウザが閉じられました。")
                cookies = [c for c in await context.cookies()
                           if c.get("domain", "").lstrip(".").endswith(COOKIE_DOMAIN)]
                header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                # The page decides nothing here: the login counts once the API accepts the session.
                if "_zane_session=" in header and api.session_is_valid(header):
                    state = await context.storage_state()
                    state["cookies"] = [c for c in state["cookies"]
                                        if c.get("domain", "").lstrip(".").endswith(COOKIE_DOMAIN)]
                    state["origins"] = []
                    return save_storage_state(state)
                await asyncio.sleep(2)
            raise SystemExit("ログインの確認が時間切れになりました。")
        finally:
            if browser.is_connected():
                await browser.close()


def login(timeout_minutes: int = 10) -> Path:
    return asyncio.run(_login_with_browser(timeout_minutes))
