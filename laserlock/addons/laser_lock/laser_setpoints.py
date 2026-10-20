"""Laser wavelength / power working range for the comb lock, and "fields follow the laser".

* Wavelength outside 1549.9–1550.2 nm → offer 1550.000 nm.
* Power below 200 µW or above 1 mW → offer 1 mW.

The wavelength and power entry fields on the Laser lock and Tunable laser pages show what the laser
reports; they stop following it while you are typing (and for ``HOLD_S`` after an edit) so a poll
never overwrites a value you are about to Set.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

WL_RANGE_NM = (1549.9, 1550.2)
WL_DEFAULT_NM = 1550.0
POWER_RANGE_W = (200e-6, 1e-3)
POWER_DEFAULT_W = 1e-3
HOLD_S = 20.0


def check(wl_nm: Optional[float], power_w: Optional[float]) -> Dict[str, Tuple[float, float]]:
    """{"wavelength_nm": (now, proposed), "power_w": (now, proposed)} for whatever is out of range."""
    out = {}
    if isinstance(wl_nm, (int, float)) and not (WL_RANGE_NM[0] <= wl_nm <= WL_RANGE_NM[1]):
        out["wavelength_nm"] = (float(wl_nm), WL_DEFAULT_NM)
    if isinstance(power_w, (int, float)) and not (POWER_RANGE_W[0] <= power_w <= POWER_RANGE_W[1] * (1 + 1e-6)):
        out["power_w"] = (float(power_w), POWER_DEFAULT_W)
    return out


def _w(x: float) -> str:
    return f"{x * 1e3:.3g} mW" if x >= 1e-3 else f"{x * 1e6:.3g} µW"


def describe(changes: Dict[str, Tuple[float, float]]) -> str:
    lines = []
    if "wavelength_nm" in changes:
        now, new = changes["wavelength_nm"]
        lines.append(f"Wavelength {now:.3f} nm is outside {WL_RANGE_NM[0]:g}–{WL_RANGE_NM[1]:g} nm → change to {new:.3f} nm")
    if "power_w" in changes:
        now, new = changes["power_w"]
        lines.append(f"Power {_w(now)} is outside {_w(POWER_RANGE_W[0])}–{_w(POWER_RANGE_W[1])} → change to {_w(new)}")
    return "\n".join(lines)


def apply(laser, changes: Dict[str, Tuple[float, float]]) -> None:
    if "wavelength_nm" in changes:
        laser.set_wavelength_nm(changes["wavelength_nm"][1])
    if "power_w" in changes:
        laser.set_power_w(changes["power_w"][1])


class FieldPull:
    """Decides when the entry fields may be refreshed from the laser."""

    def __init__(self, *widgets: Any):
        self.widgets = widgets
        self._edit_t = 0.0
        for w in widgets:
            sig = getattr(w, "textEdited", None) or getattr(w, "valueChanged", None)
            if sig is not None:
                sig.connect(lambda *_a, w=w: self._changed(w))

    def _changed(self, w):
        if w.hasFocus():                       # a change typed or scrolled by the user, not a poll
            self._edit_t = time.time()

    def clear(self) -> None:
        """After Set: follow the laser again straight away."""
        self._edit_t = 0.0

    def free(self) -> bool:
        return not any(w.hasFocus() for w in self.widgets) and time.time() - self._edit_t > HOLD_S
