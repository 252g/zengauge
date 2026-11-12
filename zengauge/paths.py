"""Per-OS locations for the saved login and the Scriptable iCloud folder."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "zengauge"
SCRIPTABLE_CONTAINER = "iCloud~dk~simonbs~Scriptable"
# Each sync writes a new timestamped file instead of replacing one: macOS attaches
# com.apple.macl to files in iCloud containers, so a file created by one app (Terminal)
# cannot be overwritten by another (launchd's python). The widget reads the newest.
PROGRESS_PREFIX = "zenstudy-progress-sync-"


def data_dir() -> Path:
    """Private folder for the saved login (storage state)."""
    if override := os.environ.get("ZENGAUGE_HOME"):
        base = Path(override)
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support" / APP_NAME
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        base.chmod(0o700)
    return base


def storage_state_path() -> Path:
    return data_dir() / "storageState.json"


def config_path() -> Path:
    return data_dir() / "config.json"


def scriptable_dir_candidates() -> list[Path]:
    """Where iCloud Drive exposes Scriptable's documents on this machine."""
    home = Path.home()
    if sys.platform == "darwin":
        return [home / "Library/Mobile Documents" / SCRIPTABLE_CONTAINER / "Documents"]
    if os.name == "nt":
        roots = [home / "iCloudDrive", Path(os.environ.get("USERPROFILE", home)) / "iCloudDrive"]
        found: list[Path] = []
        for root in dict.fromkeys(roots):
            # iCloud for Windows shows app folders either by container id or by app name.
            found += [root / SCRIPTABLE_CONTAINER / "Documents", root / SCRIPTABLE_CONTAINER,
                      root / "Scriptable"]
        return found
    return []


def find_scriptable_dir(configured: str | None = None) -> Path | None:
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_dir() else None
    for candidate in scriptable_dir_candidates():
        if candidate.is_dir():
            return candidate
    return None
