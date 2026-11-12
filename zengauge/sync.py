"""Fetch progress with the saved login and drop it into Scriptable's iCloud folder."""
from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from . import api, config, paths, session, summary


def progress_files(folder: Path) -> list[Path]:
    """Synced progress files, oldest first (names sort by their UTC timestamp)."""
    return sorted(p for p in folder.glob(paths.PROGRESS_PREFIX + "*.json") if p.is_file())


def latest(folder: Path) -> dict | None:
    for path in reversed(progress_files(folder)):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return None


def _write_new(folder: Path, payload: dict, now: datetime) -> Path:
    path = folder / f"{paths.PROGRESS_PREFIX}{now:%Y%m%dT%H%M%SZ}.json"
    tmp = folder / f".{path.name}.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.rename(tmp, path)  # the target is new, so no protected file is replaced
    for old in progress_files(folder):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass  # written by another app; harmless, the widget picks the newest
    return path


def fetch(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cookie = session.cookie_header(session.load_cookies())
    overview = api.overview(cookie)
    current = summary.pick_month(overview.get("monthly_summaries") or [], now)
    detail = None
    if current:
        try:
            detail = api.monthly(cookie, current["year"], current["month"], overview.get("service") or "basic")
        except api.ApiError:
            detail = None
    return summary.summarize(overview, detail, now)


def run(output_dir: Path | None = None) -> tuple[str, Path | None]:
    """Returns (status, written path). Status is "ok", "login_required" or "error"."""
    settings = config.load()
    target_dir = output_dir or paths.find_scriptable_dir(settings.get("scriptable_dir"))
    now = datetime.now(timezone.utc)
    source = {"host": platform.node() or "pc", "os": platform.system()}
    try:
        payload = {"status": "ok", "source": source, **fetch(now)}
        status = "ok"
    except (session.LoginRequired, api.AuthExpired) as error:
        payload = {"status": "login_required", "message": str(error), "source": source, "checkedAt": summary._iso(now)}
        status = "login_required"
    except Exception as error:  # network or unexpected response: report it, keep the last good data
        payload = {"status": "error", "message": str(error), "source": source, "checkedAt": summary._iso(now)}
        status = "error"
    if target_dir is None:
        return status, None
    if status != "ok":
        # Keep the last good numbers so the widget can still show them next to the warning.
        previous = latest(target_dir)
        if previous and previous.get("current"):
            payload = {**previous, **payload}
    return status, _write_new(target_dir, payload, now)
