"""Per-OS location for the saved login."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "zengauge"


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
