"""JDSU SWS17101 (TUNICS) tunable laser — native ASCII over GPIB (not SCPI).

Confirmed on fw V4.02: L=/L? (nm), F? (GHz), P=/P? (number, or DISABLED when
output is off), DBM/MW units, ENABLE/DISABLE, SPEED=/SPEED?, COHCTL_ON/OFF
(write-only). Replies echo 'X=value' plus trailing newlines, so every read is
gated on the GPIB status-byte data-ready bit and the prefix is stripped.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

import numpy as np

from laserlock.core.base import Device, Identity, Opt, SafetyError
from laserlock.core.units import dbm_to_w, nm_to_thz, w_to_dbm
from laserlock.core.visaio import VisaInstrument, VisaIOError

SETTLE_QUERY_S = 0.3
SETTLE_MOTOR_S = 0.8
SETTLE_ENABLE_S = 1.2
MAX_POWER_DBM = 10.0


def _speed_get(d):
    return d.query_float("SPEED?")


OPTIONS = (
    Opt("wavelength_nm", "Wavelength", "Wavelength", "number", lambda d: d.get_wavelength_nm(),
        lambda d, v: d.set_wavelength_nm(v), unit="nm"),
    Opt("frequency_ghz", "Frequency (F?)", "Wavelength", "number", lambda d: d.get_frequency_ghz(), unit="GHz"),
    Opt("speed", "Tuning speed (SPEED)", "Wavelength", "int", _speed_get, lambda d, v: d.set_speed(int(v)),
        unit="nm/s"),
    Opt("power_unit", "Power unit", "Power", "choice", lambda d: d.unit, lambda d, v: d.set_unit(v),
        choices=[("dBm", "DBM"), ("mW", "MW")], tip="Remembered by the driver (the TUNICS has no unit query)"),
    Opt("power", "Power (in the unit above)", "Power", "number", lambda d: d.get_power(),
        lambda d, v: d.set_power(v, "dBm" if d.unit == "DBM" else "mW")),
    Opt("coherence", "Coherence control (write-only)", "Power", "bool", lambda d: d.coherence_sent,
        lambda d, v: d.set_coherence_control(bool(v)), tip="COHCTL has no readback on V4.02; shows the last value sent"),
)


class SWS17101(Device):
    KIND = "sws17101"
    LABEL = "JDSU SWS17101 (TUNICS)"
    RESTORABLE = ("wavelength_nm", "power", "speed")
    OPTIONS = OPTIONS

    def __init__(self, resource: Optional[str] = None, inst=None,
                 wl_min: float = 1500.0, wl_max: float = 1640.0):
        super().__init__()
        self.io = VisaInstrument(resource, inst=inst, timeout_ms=2000)
        self.address = self.io.resource
        self.wl_min, self.wl_max = wl_min, wl_max
        self.grid_nm = 0.001
        self.coherence_sent: Optional[bool] = None   # write-only: last value sent
        self.unit = "DBM"                              # last unit written (no query on V4.02)

    def close(self) -> None:
        self.io.close()

    def safe_state(self) -> None:
        try:
            self.disable()
        except Exception:
            pass

    # ---- status-byte gated I/O -------------------------------------------------------
    def query(self, cmd: str, settle: float = SETTLE_QUERY_S, ready_timeout: float = 2.0) -> Optional[str]:
        with self.io.lock:
            self.io.write(cmd)
            time.sleep(settle)
            deadline = time.time() + ready_timeout
            while time.time() < deadline:
                try:
                    if self.io.read_stb() & 0x01:
                        break
                except Exception:
                    break
                time.sleep(0.05)
            try:
                raw = self.io.read().strip()
            except VisaIOError:
                return None
            if not raw:
                return None
            return raw.split("=", 1)[1].strip() if "=" in raw else raw

    def query_float(self, cmd: str) -> Optional[float]:
        r = self.query(cmd)
        if r is None:
            return None
        m = re.search(r"[-+]?\d+\.?\d*([eE][-+]?\d+)?", r)
        return float(m.group(0)) if m else None

    def write(self, cmd: str) -> None:
        self.io.write(cmd)
        time.sleep(0.1)

    # ---- identity --------------------------------------------------------------------
    def identify(self) -> Identity:
        raw = self.query("*IDN?") or ""
        p = [x.strip() for x in raw.split(",")]
        return Identity(self.KIND, model=p[1] if len(p) > 1 else "SWS17101",
                        serial=p[2] if len(p) > 2 else "", firmware=p[3] if len(p) > 3 else "",
                        raw=raw)

    # ---- output ----------------------------------------------------------------------
    def enable(self, confirm: bool = True) -> None:
        """Output on. (``confirm`` is accepted for older scripts and ignored.)"""
        self.write("ENABLE")
        time.sleep(SETTLE_ENABLE_S)

    output_on = enable

    def disable(self) -> None:
        self.write("DISABLE")
        time.sleep(0.3)

    output_off = disable

    # ---- "tunable_laser" capability names (same as the HP 8168) -----------------------------------
    def output_on(self, confirm: bool = True) -> None:
        self.enable()

    def output_off(self) -> None:
        self.disable()

    def set_power_uw(self, uw: float):
        return self.set_power(float(uw) / 1000.0, "mW")

    def is_on(self) -> Optional[bool]:
        r = self.query("P?")
        return None if r is None else "DISABLE" not in r.upper()

    output_is_on = is_on

    # ---- wavelength / frequency -----------------------------------------------------------
    def set_wavelength_nm(self, wl_nm: float) -> Optional[float]:
        wl_nm = float(wl_nm)
        if not (self.wl_min <= wl_nm <= self.wl_max):
            raise SafetyError(f"{wl_nm:.3f} nm outside {self.wl_min}–{self.wl_max} nm")
        self.write(f"L={wl_nm:.3f}")
        time.sleep(SETTLE_MOTOR_S)
        return self.get_wavelength_nm()

    set_wavelength = set_wavelength_nm

    def get_wavelength_nm(self) -> Optional[float]:
        return self.query_float("L?")

    def get_frequency_ghz(self) -> Optional[float]:
        return self.query_float("F?")

    def set_frequency_thz(self, thz: float):
        from laserlock.core.units import thz_to_nm
        return self.set_wavelength_nm(thz_to_nm(thz))

    def step(self, n_steps: int = 1):
        cur = self.get_wavelength_nm()
        return self.set_wavelength_nm(cur + n_steps * self.grid_nm)

    # ---- power -------------------------------------------------------------------------------
    def set_units_dbm(self): self.write("DBM"); self.unit = "DBM"
    def set_units_mw(self): self.write("MW"); self.unit = "MW"

    def set_unit(self, unit: str):
        (self.set_units_mw if str(unit).upper().startswith("MW") else self.set_units_dbm)()

    def set_power_dbm(self, dbm: float):
        return self.set_power(float(dbm), "dBm")

    def set_power_w(self, watts: float):
        return self.set_power(float(watts) * 1e3, "mW")

    def get_power_w(self) -> Optional[float]:
        p = self.get_power()
        if p is None:
            return None
        return dbm_to_w(p) if self.unit == "DBM" else p * 1e-3

    def set_power(self, value: float, unit: str = "dBm") -> Optional[float]:
        unit = unit.lower()
        if unit == "dbm":
            if value > MAX_POWER_DBM:
                raise SafetyError(f"{value} dBm above +{MAX_POWER_DBM} dBm")
            self.set_units_dbm()
        else:
            if value > 10 ** (MAX_POWER_DBM / 10):
                raise SafetyError(f"{value} mW above the +{MAX_POWER_DBM} dBm limit")
            self.set_units_mw()
        self.write(f"P={value:.2f}")
        time.sleep(SETTLE_QUERY_S)
        return self.get_power()

    def get_power(self) -> Optional[float]:
        r = self.query("P?")
        if r is None or "DISABLE" in r.upper():
            return None
        m = re.search(r"[-+]?\d+\.?\d*", r)
        return float(m.group(0)) if m else None

    # ---- speed / coherence ------------------------------------------------------------------
    def set_speed(self, speed: int):
        self.write(f"SPEED={int(speed)}")
        return self.query("SPEED?")

    def get_speed(self): return self.query("SPEED?")

    def set_coherence_control(self, on: bool):
        """Write-only on V4.02; the last value sent is remembered (unverified)."""
        self.write("COHCTL_ON" if on else "COHCTL_OFF")
        self.coherence_sent = bool(on)

    # ---- sweep ----------------------------------------------------------------------------
    def stepped_sweep(self, start_nm, stop_nm, step_nm, dwell_s=0.5, callback=None,
                      stop_event=None, confirm: bool = True):
        wls = np.arange(start_nm, stop_nm + step_nm / 2, step_nm)
        results = []
        self.enable()
        try:
            for wl in wls:
                if stop_event is not None and stop_event.is_set():
                    break
                actual = self.set_wavelength_nm(wl)
                time.sleep(dwell_s)
                results.append((actual, callback(actual) if callback else None))
        finally:
            self.disable()
        return results

    # ---- snapshot ------------------------------------------------------------------------------
    def poll(self) -> Dict[str, Any]:
        wl = self.get_wavelength_nm()
        p = self.query("P?")
        on = None if p is None else "DISABLE" not in p.upper()
        pv = None
        if on:
            m = re.search(r"[-+]?\d+\.?\d*", p)
            pv = float(m.group(0)) if m else None
        pw = None if pv is None else (dbm_to_w(pv) if self.unit == "DBM" else pv * 1e-3)
        return {"wavelength_nm": wl, "frequency_thz": nm_to_thz(wl) if wl else None,
                "power": pv, "power_unit": self.unit, "power_w": pw, "power_dbm": w_to_dbm(pw) if pw else None,
                "output_on": on, "coherence_sent": self.coherence_sent, "grid_nm": self.grid_nm}

    def snapshot(self) -> Dict[str, Any]:
        d = self.poll()
        d["speed"] = self.get_speed()
        return d

    def _setter_for(self, key):
        return {"wavelength_nm": self.set_wavelength_nm, "power": self.set_power,
                "speed": self.set_speed}.get(key)
