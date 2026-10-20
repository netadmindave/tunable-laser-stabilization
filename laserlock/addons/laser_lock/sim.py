"""Simulator for this add-on: models answer the same commands as the real instrument."""
from __future__ import annotations

import math
import re
import struct
import time
from typing import Any, Dict, Optional

import numpy as np

from laserlock.core.serialio import PortInfo
from laserlock.sim.base import RNG, OptionStore, SCPIModel, TextDevice, null_generator, num as _num


class HP8168Model(SCPIModel):
    def __init__(self, model="HP8168D", serial="3610G00108"):
        self.idn = f"HEWLETT-PACKARD,{model},{serial},5.00"
        self.wl, self.p, self.out = 1550.1e-9, 200e-6, False
        self.am_src, self.am_state, self.am_f = 2, False, 80000.0
        e = "8168E" in model
        self.wl_lim = (1475e-9, 1575e-9) if e else (1480e-9, 1570e-9)
        self.opt = OptionStore({":WAVELENGTH:REFERENCE": "1.540000000000E-06", ":WAVELENGTH:FREQUENCY": "0",
                                ":POWER:UNIT": "+0", ":POWER:ATTENUATION:AUTO": "+1", ":POWER:ATTENUATION": "0",
                                ":POWER:ATTENUATION:DARK": "+0", ":SOURCE:MODOUT": "+0",
                                ":STATUS:QUESTIONABLE:CONDITION": "+0", ":LOCK": "+0", ":DISPLAY:ENABLE": "+1",
                                ":SYSTEM:DATE": "26/10/14", ":SYSTEM:TIME": "09:30:00"})

    def handle(self, c):
        u = c.upper()
        if u == "*IDN?": return self.idn
        if u == "*OPT?": return "PASSIVE COMPONENT TEST,0,0,COHERENCE CONTROL"
        if u == ":SYSTEM:ERROR?": return '+0,"No error"'
        if u in ("*CLS", "*GTL", "*RST"): return None
        if u == ":WAVELENGTH?": return f"{self.wl:.12E}"
        if u == ":WAVELENGTH? MIN": return f"{self.wl_lim[0]:.12E}"
        if u == ":WAVELENGTH? MAX": return f"{self.wl_lim[1]:.12E}"
        if u.startswith(":WAVELENGTH "): self.wl = _num(u.split()[1]); return None
        if u == ":WAVELENGTH:REFERENCE:DISPLAY": self.opt.set(":WAVELENGTH:REFERENCE", f"{self.wl:.12E}"); return None
        if u == ":POWER?": return f"{self.p:.6E}"
        if u == ":POWER? MAX": return "1.6E-03"
        if u.startswith(":POWER "): self.p = _num(u.split()[1]); return None
        if u == ":OUTPUT?": return "+1" if self.out else "+0"
        if u.startswith(":OUTPUT "): self.out = u.endswith("ON"); return None
        if u == ":SOURCE:AM:SOURCE?": return f"+{self.am_src}"
        if u.startswith(":SOURCE:AM:SOURCE "): self.am_src = int(_num(u)); return None
        if u == ":SOURCE:AM:STATE?": return "+1" if self.am_state else "+0"
        if u.startswith(":SOURCE:AM:STATE "): self.am_state = u.endswith("ON"); return None
        if u == ":SOURCE:AM:INTERNAL:FREQUENCY?": return f"{self.am_f:.1f}"
        if u.startswith(":SOURCE:AM:INTERNAL:FREQUENCY "): self.am_f = _num(u.split()[1]); return None
        if u in ("*STB?", "*ESR?", ":STATUS:OPERATION:CONDITION?"): return "+0"
        return self.opt.handle(c)

class SWSModel(SCPIModel):
    def __init__(self):
        self.wl, self.p, self.on, self.speed = 1550.0, 0.0, False, 10

    def handle(self, c):
        u = c.upper()
        if u == "*IDN?": return "JDS_Uniphase,SWS17101,0,V4.02"
        if u == "L?": return f"L={self.wl:.3f}"
        if u.startswith("L="): self.wl = float(u[2:]); return None
        if u == "F?": return f"F={299792458.0 / (self.wl * 1e-9) / 1e9:.1f}"
        if u == "P?": return f"P={self.p:.2f}" if self.on else "P=DISABLED"
        if u.startswith("P="): self.p = float(u[2:]); return None
        if u == "ENABLE": self.on = True; return None
        if u == "DISABLE": self.on = False; return None
        if u == "SPEED?": return f"SPEED={self.speed}"
        if u.startswith("SPEED="): self.speed = int(u[6:]); return None
        if u in ("DBM", "MW", "COHCTL_ON", "COHCTL_OFF"): return None
        return None

class RigolModel(SCPIModel):
    def __init__(self, world):
        self.w = world
        self.tb, self.tbo, self.mdepth, self.acq = 20e-9, 0.0, 10_000, "NORM"
        self.ch = {n: {"DISP": "1" if n <= 2 else "0", "SCAL": 0.2, "OFFS": 0.0, "COUP": "DC",
                       "BWL": "OFF", "PROB": 1.0, "IMP": "FIFT", "UNIT": "VOLT", "INV": "OFF"}
                   for n in range(1, 5)}
        self.trig = {"MODE": "EDGE", "SWE": "AUTO", "COUP": "DC", "SRC": "CHAN1", "SLOP": "POS",
                     "LEV": 0.0, "HOLD": 8e-9}
        self.wav = {"SRC": 1, "MODE": "MAX", "FMT": "WORD", "PTS": 1000, "START": 1, "STOP": 1000}
        self.status_seq = []
        self.awg = ("SIN", 1000.0)
        self.opt = OptionStore({":SYSTEM:RCLOCK": "COUT", ":TIMEBASE:VERNIER": "0", ":TIMEBASE:DELAY:ENABLE": "0",
                                ":TIMEBASE:DELAY:SCALE": "1.0E-08", ":TRIGGER:NREJECT": "0", ":DISPLAY:GRID": "FULL",
                                ":DISPLAY:WBRIGHTNESS": "50", ":DISPLAY:GRADING:TIME": "MIN",
                                ":SOURCE1:OUTPUT:STATE": "0", ":SOURCE1:VOLTAGE": "1.0", ":SOURCE1:VOLTAGE:OFFSET": "0",
                                ":SYSTEM:BEEPER": "0"})
        for n in range(1, 5):
            self.opt.set(f":CHANNEL{n}:VERNIER", "0")
            self.opt.set(f":CHANNEL{n}:LABEL:CONTENT", f'"CH{n}"')

    def srate(self):
        return min(4e9, self.mdepth / (self.tb * 10))

    def handle(self, c):
        u = c.upper()
        if u == "*IDN?": return "RIGOL TECHNOLOGIES,MHO5104,MHO5C283M0017,00.01.02"
        if u in ("*CLS", ":RUN", ":STOP", ":CLEAR", ":TRIGGER:FORCE", ":AUTOSCALE", ":AUTOSET"):
            if u == ":STOP": self.status_seq = []
            return None
        if u == ":SINGLE":
            self.status_seq = ["WAIT", "TD", "STOP"]; return None
        if u == ":TRIGGER:STATUS?":
            return self.status_seq.pop(0) if self.status_seq else "STOP"
        if u == ":SYSTEM:ERROR?": return '0,"No error"'
        if u.startswith(":SYSTEM:RCLOCK "):
            self.opt.set(":SYSTEM:RCLOCK", u.split()[1]); return None
        m = re.match(r":TIMEBASE:MAIN:SCALE\s+(\S+)", u)
        if m: self.tb = float(m.group(1)); return None
        m = re.match(r":TIMEBASE:MAIN:OFFSET\s+(\S+)", u)
        if m: self.tbo = float(m.group(1)); return None
        if u.startswith(":TIMEBASE:MODE "): return None
        if u == ":TIMEBASE:MAIN:SCALE?": return f"{self.tb:.6E}"
        if u == ":TIMEBASE:MAIN:OFFSET?": return f"{self.tbo:.6E}"
        if u == ":TIMEBASE:MODE?": return "MAIN"
        m = re.match(r":CHANNEL(\d):(\w+)(\?|\s+(\S+))", u)
        if m:
            n, k = int(m.group(1)), m.group(2)[:4]
            key = {"DISP": "DISP", "SCAL": "SCAL", "OFFS": "OFFS", "COUP": "COUP", "BWLI": "BWL",
                   "PROB": "PROB", "IMPE": "IMP", "UNIT": "UNIT", "INVE": "INV"}.get(k)
            if key is None: return self.opt.handle(c)
            if m.group(3) == "?":
                v = self.ch[n][key]
                return f"{v:.6E}" if isinstance(v, float) else str(v)
            val = m.group(4)
            if key == "DISP": val = "1" if val in ("ON", "1") else "0"
            elif isinstance(self.ch[n][key], float): val = float(val)
            self.ch[n][key] = val
            return None
        if u.startswith(":ACQUIRE:MDEPTH "):
            a = u.split()[1]
            self.mdepth = 10_000 if a == "AUTO" else int(float(a)); return None
        if u.startswith(":ACQUIRE:TYPE "): self.acq = u.split()[1]; return None
        if u.startswith(":ACQUIRE:AVERAGES "): return None
        if u == ":ACQUIRE:MDEPTH?": return str(self.mdepth)
        if u == ":ACQUIRE:TYPE?": return self.acq
        if u == ":ACQUIRE:AVERAGES?": return "4"
        if u == ":ACQUIRE:SRATE?": return f"{self.srate():.6E}"
        m = re.match(r":TRIGGER:(?:EDGE:)?(\w+)(\?|\s+(\S+))", u)
        if m:
            k = m.group(1)[:4]
            mp = {"MODE": "MODE", "SWEE": "SWE", "COUP": "COUP", "SOUR": "SRC", "SLOP": "SLOP",
                  "LEVE": "LEV", "HOLD": "HOLD"}.get(k)
            if mp is None: return self.opt.handle(c)
            if m.group(2) == "?": return str(self.trig[mp])
            self.trig[mp] = m.group(3); return None
        if u.startswith(":TRIGGER:"): return self.opt.handle(c)
        m = re.match(r":MEASURE:ITEM\? (\w+),CHANNEL(\d)", u)
        if m:
            item = m.group(1)
            vals = {"FREQUENCY": 25e6, "PERIOD": 40e-9, "VAMP": 0.612, "VMAX": 0.306, "VMIN": -0.306,
                    "VRMS": 0.216, "VAVG": -0.0012, "RTIME": 13.4e-9}
            return f"{vals.get(item, 9.9e37):.6E}"
        m = re.match(r":WAVEFORM:(\w+)(\?|\s+(\S+))", u)
        if m:
            k, q, v = m.group(1), m.group(2) == "?", m.group(3)
            if k == "SOURCE":
                if q: return f"CHAN{self.wav['SRC']}"
                self.wav["SRC"] = int(v[-1]); return None
            if k == "MODE": return "MAX" if q else None
            if k == "FORMAT":
                if not q: self.wav["FMT"] = v
                return None if not q else self.wav["FMT"]
            if k == "POINTS":
                if q: return str(self.wav["PTS"])
                self.wav["PTS"] = min(int(v), self.wav["STOP"] - self.wav["START"] + 1, self.mdepth)
                return None
            if k == "START": self.wav["START"] = int(v); return None
            if k == "STOP": self.wav["STOP"] = int(v); return None
            if k == "PREAMBLE":
                dt = 1 / self.srate()
                yinc = self.ch[self.wav["SRC"]]["SCAL"] * 8 / 65536 if self.wav["FMT"] == "WORD" \
                    else self.ch[self.wav["SRC"]]["SCAL"] * 8 / 256
                yref = 32768 if self.wav["FMT"] == "WORD" else 128
                return (f"{1 if self.wav['FMT']=='WORD' else 0},0,{self.wav['PTS']},1,"
                        f"{dt:.6E},{-self.tb * 5:.6E},0,{yinc:.6E},0,{yref}")
        if u.startswith(":MATH"): return None if "?" not in u else "OFF"
        if u == ":SOURCE1:FUNCTION?": return self.awg[0]
        if u == ":SOURCE1:FREQUENCY?": return f"{self.awg[1]:.6E}"
        if u.startswith(":SOURCE1:FUNCTION "): self.awg = (u.split()[1], self.awg[1]); return None
        if u.startswith(":SOURCE1:FREQUENCY "): self.awg = (self.awg[0], _num(u.split()[1])); return None
        if u.startswith(":CURSOR"): return None if "?" not in u else "[]"
        if u in ("*STB?", "*ESR?"): return "0"
        return self.opt.handle(c)

    def binary(self, cmd):
        u = cmd.upper()
        if u == ":WAVEFORM:DATA?":
            n = self.wav["STOP"] - self.wav["START"] + 1
            dt = 1 / self.srate()
            t = (self.wav["START"] - 1 + np.arange(n)) * dt
            ch = self.wav["SRC"]
            f0, amp = 25e6, 0.306
            rms = self.w.beat_phase_rms() if ch == 1 else 0.05
            if ch == 2:                                    # CH2: the laser–comb beat (OPL #2 input)
                lb = getattr(self.w, "laser_beat_hz", lambda: None)()
                opl2 = self.w.models.get("opl2")
                locked = bool(opl2 is not None and getattr(opl2, "locked", False))
                if locked:
                    lb = opl2.p["BNTGT"] * 1e6
                f0, amp, rms = (lb or 1e6), (0.1 if lb else 0.0), (0.3 if locked else 0.8)
            # phase noise band-limited to 500 kHz with the requested rms
            Ph = np.fft.rfft(RNG.normal(0, 1, n))
            fr = np.fft.rfftfreq(n, dt)
            Ph[(fr > 5e5) | (fr == 0)] = 0
            ph = np.fft.irfft(Ph, n)
            ph = ph / (ph.std() + 1e-12) * rms
            v = amp * np.sin(2 * np.pi * f0 * t + ph + (0 if ch == 1 else np.pi / 2))
            v += RNG.normal(0, 0.002, n)
            scal = self.ch[ch]["SCAL"]
            if self.wav["FMT"] == "WORD":
                code = np.clip(np.round(v / (scal * 8 / 65536) + 32768), 0, 65535).astype(np.uint16)
            else:
                code = np.clip(np.round(v / (scal * 8 / 256) + 128), 0, 255).astype(np.uint8)
            return code
        if u == ":DISPLAY:DATA?":
            return bytearray(b"BM" + bytes(60))
        return None



C = 299792458.0
LOCK_WL_NM = 1550.100          # at this wavelength the laser sits 51.8 MHz from a comb tooth


def install(world) -> None:
    """OPL #2 on COM11, HP 8168E + SWS17101 on GPIB, Rigol on USB.

    The OPL #2 beat exists only while a laser output is on: 51.8 MHz at 1550.100 nm (1.8 MHz above the
    50 MHz target, so the beat check has something to find), moving 1 MHz per MHz of optical detuning.
    The OPL counter sees the beat only within ±1 MHz of its target; its servo captures within ±100 kHz."""
    from .opl_sim import OPLModel

    hp, sws = HP8168Model("HP8168E", "3610G00108"), SWSModel()
    world.models.update(laser_hp=hp, laser_sws=sws)

    def laser_beat_hz():
        if getattr(hp, "out", False):
            wl = hp.wl * 1e9
        elif getattr(sws, "on", False):
            wl = sws.wl
        else:
            return None
        return 51.8e6 + (C / (wl * 1e-9) - C / (LOCK_WL_NM * 1e-9))

    world.laser_beat_hz = laser_beat_hz

    class LaserBeatOPL(OPLModel):
        CAPTURE_HZ = 100e3

        @property
        def has_beat(self):
            b = laser_beat_hz()
            return b is not None and abs(b - self.p["BNTGT"] * 1e6) < 1e6

        @has_beat.setter
        def has_beat(self, v):
            pass

    world.opl2 = LaserBeatOPL(world, "OPL-0002", 50.0, has_beat=False, pll=(7.0, 12.0, 9.5))
    world.models["opl2"] = world.opl2
    base = world.beat_offset_hz

    def beat_offset_hz(opl):
        if opl is world.opl2:
            b = laser_beat_hz()
            return (b - opl.p["BNTGT"] * 1e6) if b is not None else 1e9
        return base(opl)

    world.beat_offset_hz = beat_offset_hz
    world.add_serial(PortInfo("COM11", "USB Serial Device (COM11)", "USB VID:PID=1FC9:0084 SER=OPL0002",
                              0x1FC9, 0x0084, "OPL0002"), world.opl2, b"\r")

    def rf():
        b = laser_beat_hz()
        if b is None or not (1e6 < b < 2e9):
            return []
        return [(world.opl2.p["BNTGT"] * 1e6 if world.opl2.locked else b, -47.0)]

    world.add_rf_line(rf)
    world.add_visa("GPIB2::2::INSTR", hp)
    world.add_visa("GPIB2::10::INSTR", sws)
    world.rigol = RigolModel(world)
    world.add_visa("USB0::0x1AB1::0x0450::MHO5C283M0017::INSTR", world.rigol)
    from .hp8563e_sim import install as _install_sa      # HP 8563E on GPIB0::18 (optional beat instrument)
    _install_sa(world)
