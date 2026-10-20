"""Cross-app instrument claims: an instrument connected in one app can't be connected in another.

Each app writes one small file per connected instrument into a shared folder
(``%LOCALAPPDATA%\\BenchClaims``; override with ``BENCH_CLAIMS_DIR``). Before opening an instrument an
app checks for a claim held by another *running* app and refuses ("in use by Laser Lock"); scans skip
claimed addresses so probing never talks to an instrument another app is driving. Claims are removed on
disconnect and on exit; a claim left by a crashed app is ignored because its process is gone.

This file is the same in every app except ``APP``.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

APP = "Laser Lock"


def folder() -> Path:
    env = os.environ.get("BENCH_CLAIMS_DIR")
    base = Path(env) if env else Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "BenchClaims"
    base.mkdir(parents=True, exist_ok=True)
    return base


def key(address: str) -> str:
    """One key per physical instrument: USB VISA resources by vendor/product/serial (the '::0::' interface
    number and suffix are dropped), everything else by its normalised address."""
    a = (address or "").strip().upper()
    if a.startswith("USB"):
        parts = a.split("::")
        if len(parts) >= 4:
            return "USB-" + "-".join(parts[1:4])
    if a.startswith("GPIB"):
        m = re.match(r"GPIB(\d*)::(\d+)", a)
        if m:
            return f"GPIB{m.group(1) or '0'}-{m.group(2)}"
    return re.sub(r"[^A-Z0-9]+", "-", a).strip("-") or "UNKNOWN"


def _path(address: str) -> Path:
    return folder() / f"{key(address)}.json"


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:   # STILL_ACTIVE
                return False
            buf = ctypes.create_unicode_buffer(1024)       # a reused pid that isn't Python isn't ours
            size = wintypes.DWORD(1024)
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                name = buf.value.lower()
                return "python" in name or "lab-tools" in name or "laser-lock" in name or "vescent-comb" in name
            return True
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def holder(address: str) -> Optional[str]:
    """Name of another running app that holds this instrument, else None."""
    if not address:
        return None
    d = _read(_path(address))
    if not d or int(d.get("pid", 0)) == os.getpid() or not _alive(int(d.get("pid", 0))):
        return None
    return str(d.get("app") or "another app")


def claim(address: str) -> Optional[str]:
    """Claim the instrument for this app. Returns None on success, or the name of the app holding it."""
    if not address:
        return None
    p = _path(address)
    for _ in range(2):
        try:
            fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            d = _read(p) or {}
            pid = int(d.get("pid", 0))
            if pid == os.getpid():
                return None
            if _alive(pid):
                return str(d.get("app") or "another app")
            try:
                p.unlink()                                  # stale: its app is gone
            except OSError:
                pass
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"app": APP, "pid": os.getpid(), "address": address, "since": time.time()}, fh)
        return None
    return "another app"


def release(address: str) -> None:
    if not address:
        return
    p = _path(address)
    d = _read(p)
    if d and int(d.get("pid", 0)) == os.getpid():
        try:
            p.unlink()
        except OSError:
            pass


def release_all() -> None:
    try:
        for p in folder().glob("*.json"):
            d = _read(p)
            if d and int(d.get("pid", 0)) == os.getpid():
                try:
                    p.unlink()
                except OSError:
                    pass
    except Exception:
        pass


class InUse(RuntimeError):
    def __init__(self, address: str, app: str):
        super().__init__(f"in use by {app} — disconnect it there first")
        self.address, self.app = address, app


atexit.register(release_all)
