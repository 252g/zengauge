"""Run `sync` every N minutes: launchd on macOS, Task Scheduler on Windows."""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from . import paths

LABEL = "local.zengauge.sync"
TASK_NAME = "zengauge sync"
ENTRY = Path(__file__).resolve().parent.parent / "zengauge.py"


def _python(windowless: bool) -> str:
    exe = Path(sys.executable)
    if windowless and os.name == "nt":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def _plist_path() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"


def install(minutes: int) -> str:
    if sys.platform == "darwin":
        log = paths.data_dir() / "sync.log"
        plist = {
            "Label": LABEL,
            "ProgramArguments": [_python(False), str(ENTRY), "sync", "--quiet"],
            "StartInterval": minutes * 60,
            "RunAtLoad": True,
            "StandardOutPath": str(log),
            "StandardErrorPath": str(log),
        }
        path = _plist_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(path)], capture_output=True)
        path.write_bytes(plistlib.dumps(plist))
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)], check=True)
        return f"{minutes}分ごとの自動更新を登録しました（{path}）"
    if os.name == "nt":
        command = f'"{_python(True)}" "{ENTRY}" sync --quiet'
        subprocess.run(["schtasks", "/Create", "/F", "/SC", "MINUTE", "/MO", str(minutes),
                        "/TN", TASK_NAME, "/TR", command], check=True, capture_output=True)
        return f"{minutes}分ごとの自動更新をタスクスケジューラに登録しました（{TASK_NAME}）"
    raise SystemExit("自動更新の登録は macOS と Windows のみ対応です。cron などで `sync` を実行してください。")


def uninstall() -> str:
    if sys.platform == "darwin":
        path = _plist_path()
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(path)], capture_output=True)
        path.unlink(missing_ok=True)
        return "自動更新を解除しました"
    if os.name == "nt":
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True)
        return "自動更新を解除しました"
    raise SystemExit("自動更新の解除は macOS と Windows のみ対応です。")


def installed() -> bool:
    if sys.platform == "darwin":
        return _plist_path().exists()
    if os.name == "nt":
        return subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME], capture_output=True).returncode == 0
    return False
