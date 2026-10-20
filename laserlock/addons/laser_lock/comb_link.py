"""Comb state from the Vescent Comb application.

That application writes ``comb_status.json`` next to its settings file about once a second
(FFC-100 mode lock, OPL #1 f_rep lock to GPS, SLICE-FPGA-II f_ceo lock and CEO reference).
This app never talks to the comb instruments; it only reads that file.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

STALE_S = 10.0


def default_path() -> Path:
    env = os.environ.get("VESCENTCOMB_SETTINGS")
    if env:
        return Path(env).parent / "comb_status.json"
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "vescentcomb" / "comb_status.json"


def status_path(settings=None) -> Path:
    p = settings.get("ui.laser.comb_status_path") if settings is not None else None
    return Path(p) if p else default_path()


def read_status(settings=None) -> Dict[str, Any]:
    """The last comb status, plus ``age_s`` and ``ok_file``. ``{}``-like dict when missing."""
    path = status_path(settings)
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {"ok_file": False, "path": str(path)}
    d["ok_file"] = True
    d["path"] = str(path)
    d["age_s"] = time.time() - float(d.get("t", 0) or 0)
    return d


def verdict(st: Dict[str, Any]) -> Tuple[str, str]:
    """(text, kind) for a pill: ok / warn / bad / idle."""
    if not st.get("ok_file"):
        return "Comb app not running", "idle"
    if st.get("age_s", 1e9) > STALE_S:
        return f"comb status {st['age_s']:.0f} s old", "warn"
    if st.get("comb_locked"):
        return "comb locked", "ok"
    why = []
    if st.get("ffc", {}).get("mode_locked") is False:
        why.append("not mode-locked")
    if not st.get("opl1", {}).get("frep_locked"):
        why.append("f_rep open")
    if st.get("fpga", {}).get("ceo_locked") is False:
        why.append("f_ceo open")
    return "comb: " + (", ".join(why) or "not locked"), "bad"


def comb_locked(settings=None, require: bool = True) -> Tuple[bool, str]:
    """For the laser lock sequence: (ok, note). ``require=False`` lets a missing comb app pass."""
    st = read_status(settings)
    text, kind = verdict(st)
    if kind == "ok":
        ph = st.get("fpga", {}).get("ceo_phase_rad")
        return True, "comb locked" + (f" · f_ceo {ph:.2f} rad" if isinstance(ph, (int, float)) else "")
    if not require and kind == "idle":
        return True, "comb app not running — comb check skipped"
    return False, text


def fceo_hz(settings=None) -> Optional[float]:
    st = read_status(settings)
    if not st.get("ok_file") or st.get("age_s", 1e9) > STALE_S:
        return None
    v = st.get("fpga", {}).get("ceo_ref_hz")
    return float(v) if isinstance(v, (int, float)) and v > 0 else None
