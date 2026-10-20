"""Laser-lock cards for the Overview page."""
from __future__ import annotations

from laserlock.gui.cards import RoleCard


class OPL2Card(RoleCard):
    ROLE, TITLE, OPEN_PAGE = "opl2", "SLICE-OPL #2 · laser → comb", "laserlock"
    FIELDS = [("servo_on", "Servo", "{}"), ("beatnote", "Counter", "si:Hz:1e6:9"),
              ("target_beatnote", "Target", "si:Hz:1e6:7"), ("pll_out_v", "PLL out", "si:V:1:4")]

    def transform(self, d):
        b = d.get("beatnote")
        has = isinstance(b, float) and b > 1
        servo = d.get("servo_on")
        d["servo_on"] = "ON" if servo else "off"
        if not has:
            d["beatnote"] = "no beat"
        text = "locked" if servo and has else ("no beat" if not has else "servo off")
        return d, text, ("ok" if servo and has else "warn")


class LaserCard(RoleCard):
    ROLE, TITLE = "laser", "Tunable laser"
    FIELDS = [("wavelength_nm", "Wavelength", "{:.3f} nm"), ("frequency_thz", "Frequency", "si:Hz:1e12:8"),
              ("power_disp", "Power", "{}"), ("output_on", "Output", "{}")]

    def transform(self, d):
        on = d.get("output_on")
        if isinstance(d.get("power_w"), float):
            from laserlock.core.units import eng, w_to_dbm
            d["power_disp"] = f"{eng(d['power_w'], 'W', 4)} · {w_to_dbm(d['power_w']):.2f} dBm" if d["power_w"] > 0 \
                else "0 W"
        elif isinstance(d.get("power"), float):
            d["power_disp"] = f"{d['power']:.2f} dBm"
        d["output_on"] = "ON" if on else "off"
        return d, ("Output on" if on else "Output off"), ("warn" if on else "idle")
