"""Small JSON settings file (currently only an explicit Scriptable folder)."""
from __future__ import annotations

import json

from . import paths


def load() -> dict:
    path = paths.config_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(values: dict) -> None:
    paths.config_path().write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")
