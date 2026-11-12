"""Read-only access to ZEN Study's report progress API (GET only)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "https://api.nnn.ed.nico/v2/dashboard/report_progresses"
USER_AGENT = "zengauge/1.0"


class AuthExpired(Exception):
    pass


class ApiError(Exception):
    pass


def get_json(path: str, cookie: str, timeout: float = 20) -> dict:
    request = urllib.request.Request(BASE + path, headers={
        "Cookie": cookie, "Accept": "application/json", "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise AuthExpired("ログインが切れています") from None
        raise ApiError(f"サーバーエラー ({error.code})") from None
    except urllib.error.URLError as error:
        raise ApiError(f"通信できませんでした ({error.reason})") from None


def session_is_valid(cookie: str) -> bool:
    try:
        get_json("", cookie, timeout=10)
        return True
    except (AuthExpired, ApiError):
        return False


def overview(cookie: str) -> dict:
    return get_json("", cookie)


def monthly(cookie: str, year: int, month: int, service: str) -> dict:
    return get_json(f"/monthly/{year}/{month}?service={urllib.request.quote(service)}", cookie)
