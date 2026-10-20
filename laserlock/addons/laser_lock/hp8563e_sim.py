"""Simulated HP 8563E for Laser Lock: shows the laser↔comb beat (narrow when OPL #2 is locked)."""
from __future__ import annotations

import math
import re
import time

import numpy as np

from laserlock.sim.base import RNG, OptionStore, SCPIModel, num as _num


class HP8563EModel(SCPIModel):
    def __init__(self, world):
        self.w = world
        self.cf, self.sp, self.rl, self.rb, self.vb = 50e6, 20e6, 0.0, 100e3, 100e3
        self.mkf = self.cf
        self.opt = OptionStore({"FREF": "INT", "LG": "10", "AUNITS": "DBM", "AT": "10", "DET": "POS", "TM": "FREE",
                                "VAVG": "100", "ST": "0.05", "SS": "1E6", "FOFFSET": "0", "VBR": "1", "RBR": "0.011",
                                "ROFFSET": "0", "DL": "-120", "TH": "-120", "MKFC": "0", "MKFCR": "1000",
                                "MKTRACK": "0", "MKNOISE": "0", "MKPX": "6", "ERR": "0"})


    def handle(self, c):
        u = c.upper()
        if u == "*IDN?": return None            # this unit does not answer *IDN?
        if u == "ID?": return "HP8563E"
        if u in ("IP", "IP;"): self.opt.set("FREF", "INT"); return None      # preset → internal reference
        if u == "SER?": return "3425A01234"
        if u == "DONE?": return "1"
        m = re.match(r"(CF|SP|RL|RB|VB|FA|FB|MKF)\s+([-+0-9.E]+)", u)
        if m:
            k, v = m.group(1), float(m.group(2))
            if k == "CF": self.cf = v
            elif k == "SP": self.sp = v
            elif k == "RL": self.rl = v
            elif k == "RB": self.rb = v
            elif k == "VB": self.vb = v
            elif k == "MKF": self.mkf = v
            elif k == "FA": self.cf, self.sp = v + self.sp / 2, self.sp
            elif k == "FB": self.sp = v - (self.cf - self.sp / 2); self.cf = v - self.sp / 2
            return None
        if u in ("FS",):
            self.cf, self.sp = 13.25e9, 26.5e9; return None
        q = {"CF?": self.cf, "SP?": self.sp, "RL?": self.rl, "RB?": self.rb, "VB?": self.vb,
             "FA?": self.cf - self.sp / 2, "FB?": self.cf + self.sp / 2}
        if u in q: return f"{q[u]:.6E}"
        if u.startswith("TDF P"):
            p = self._trace()[1]
            if self.opt.get("LG") in ("0", 0):                 # linear scale: watts
                return ",".join(f"{10 ** (x / 10) * 1e-3:.4E}" for x in p)
            return ",".join(f"{x:.2f}" for x in p)
        if u == "LN":
            self.opt.set("LG", "0"); return None
        if u.startswith("LG "):
            self.opt.set("LG", str(int(_num(u)))); return None
        if u == "MKPK HI":
            f, p = self._trace(); self.mkf = f[int(np.argmax(p))]; return None
        if u == "MKF?": return f"{self.mkf:.6E}"
        if u == "MKA?":
            f, p = self._trace(); return f"{p[int(np.argmin(abs(f - self.mkf)))]:.2f}"
        return self.opt.handle(c)

    def _trace(self):                                    # Laser Lock: the beat from the simulated laser
        f = np.linspace(self.cf - self.sp / 2, self.cf + self.sp / 2, 601)
        p = -85 + RNG.normal(0, 1.2, 601)
        b = getattr(self.w, "laser_beat_hz", lambda: None)()
        if b:
            opl = self.w.models.get("opl2")
            locked = bool(opl is not None and getattr(opl, "locked", False))
            width = 1.0 if locked else 150e3                       # free-running beat: broad and wandering
            f0 = b + (0 if locked else RNG.normal(0, 50e3))
            hw = max(self.rb, width) / 2
            p = np.maximum(p, -25 - 10 * np.log10(1 + ((f - f0) / hw) ** 2))
        return f, p


def install(world) -> None:
    world.add_visa("GPIB0::18::INSTR", HP8563EModel(world))
