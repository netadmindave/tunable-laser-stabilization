"""Simulated SLICE-OPL (OPL #2)."""
from __future__ import annotations

import math
import re
import struct
import time
from typing import Any, Dict, Optional

import numpy as np

from laserlock.core.serialio import PortInfo
from laserlock.sim.base import RNG, SCPIModel, TextDevice, null_generator, num as _num


class OPLModel(TextDevice):
    eol = "\r\n"
    COUNTER_LOW_HZ = 31.0   # the OPL counter reads ~31 Hz low (approximate counter)

    def __init__(self, world, serial: str, target_mhz: float, has_beat: bool = True,
                 pll=(0.0, 10.0, 5.0)):
        self.w = world
        self.serial = serial
        self.p: Dict[str, Any] = {
            "SERVO": "OFF", "BNTGT": target_mhz, "PLLINVT": "OFF", "PLLGAIN": -55.0,
            "INT": 100.0, "DIFF": 0.0, "GAINLIM": "OFF", "PLLBIAS": pll[2], "PLLMAX": pll[1],
            "PLLMIN": pll[0], "LOCKRNG": 0.1, "AUXEN": "OFF", "AUXINVT": "OFF", "AUXTGT": 5.0,
            "AUXGAIN": 1.0, "AUXBIAS": 0.0, "AUXMAX": 10.0, "AUXMIN": 0.0, "RAMP": "OFF",
            "RAMPCH": 0, "RAMPNUM": 200, "RAMPFRQ": 10.0, "RAMPSWP": 1.0, "RAMPADC": 128,
            "BNMAX": 1000.0, "N1DIV": 1, "N2DIV": 100, "EREFBWL": 12.0, "PFDDDS": "ON",
            "DDSINT": "OFF", "DDSREFF": 10.0, "M1DIV": 1, "M2DIV": 1, "MUXO": 0, "FP1EN": "OFF",
            "FP2EN": "OFF", "FPMUXO": 1, "FPAINEN": "OFF", "FPBINEN": "OFF", "TRIGI": 0,
            "TRIGO": 0, "HOLD": "OFF", "DDSFREQ": 10.0, "DDSRAW": 0,
            "#SCBKLT": 80, "#SCVOL": 20,
        }
        self.has_beat = has_beat
        self.locked = False

    # physics -------------------------------------------------------------------------
    def true_beat_hz(self) -> float:
        tgt = self.p["BNTGT"] * 1e6
        if not self.has_beat:
            return 0.0
        if self.locked:
            return tgt
        return tgt + self.w.beat_offset_hz(self)

    def servo_quality(self):
        """Lock lost above about -43 dB gain (used by the auto-tune simulation)."""
        return self.p["PLLGAIN"] <= -43.0

    def update_lock(self):
        """Like the bench: once the servo is on without a lock the integrator rails, and it stays railed
        (won't capture even if the beat comes within range) until the servo is switched off."""
        if self.p["SERVO"] != "ON":
            self.locked = self.railed = False
            return
        if not self.has_beat:
            self.locked, self.railed = False, True
            return
        if not self.locked:
            if getattr(self, "railed", False):
                return
            off = abs(self.w.beat_offset_hz(self))
            self.locked = off < getattr(self, "CAPTURE_HZ", 300.0) and self.servo_quality()
            self.railed = not self.locked
        elif not self.servo_quality():
            self.locked, self.railed = False, True

    def handle(self, cmd: str) -> Optional[str]:
        self.update_lock()
        parts = cmd.split()
        tok = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else None
        if tok == "*IDN?":
            return f"Vescent Photonics,SLICE-OPL,{self.serial},SC 1.242,OPL 1.27"
        if tok == "*RST":
            return "OK"
        if tok == "READBN?":
            if not self.has_beat or getattr(self, "counter_blind", False):   # bench: OPL #2 counter never sees it
                return "READBN 0.000000"
            b = self.true_beat_hz() - self.COUNTER_LOW_HZ + RNG.normal(0, 2.0)
            return f"READBN {b / 1e6:.6f}"
        if tok == "READREF?":
            return "READREF 10.000000"
        if tok == "READVOLT":
            ch = int(_num(arg or "1"))
            lo, hi = self.p["PLLMIN"], self.p["PLLMAX"]
            if self.locked:
                err, out = RNG.normal(0.012, 0.002), self.p["PLLBIAS"] + 0.21
            elif self.p["SERVO"] == "ON":
                err, out = 2.5, hi
            else:
                err, out = RNG.normal(0, 0.3), self.p["PLLBIAS"]
            vals = {1: err, 2: err * 8, 3: out - self.p["PLLBIAS"], 4: out, 5: 0.0,
                    6: 0.3, 7: 0.9, 8: 0.0}
            return f"READVOLT {vals.get(ch, 0.0):.4f}"
        if tok == "NOCP":
            self.p["HOLD"] = "ON"; return "OK"
        if tok == "DDSAUTO":
            return "OK"
        if tok.endswith("?"):
            key = tok[:-1]
            if key in self.p:
                return f"{key} {self.p[key]}"
            return "ERR"
        if tok in self.p:
            v = arg
            if isinstance(self.p[tok], (int, float)) and not isinstance(self.p[tok], bool):
                v = type(self.p[tok])(float(arg))
            else:
                v = str(arg).upper()
            self.p[tok] = v
            if tok == "SERVO":
                self.update_lock()
            return "OK"
        return "ERR"

