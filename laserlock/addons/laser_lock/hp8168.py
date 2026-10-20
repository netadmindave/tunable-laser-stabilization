"""HP / Agilent 8168D and 8168E tunable laser sources (GPIB, SCPI-like).

Verified against HP8168D fw 5.00. Wavelength on the bus is in metres, power
in watts. The model sets range and the tuning grid:
8168D 1480–1570 nm, 100 pm grid; 8168E 1475–1575 nm, 10 pm grid (your notebook's
measured step; the 8168E manual specifies 1 pm resolution — ``grid_nm`` can be changed).
The 8168E programming manual lists coherence control as AM source INT2 (``:SOURce:AM:SOURce 1``);
on the fw 5.00 unit it did not respond, so keep it OFF unless you have checked it.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import numpy as np

from laserlock.core.base import Device, DeviceError, Identity, Opt, SafetyError
from laserlock.core.units import dbm_to_w, nm_to_thz, w_to_dbm
from laserlock.core.visaio import VisaInstrument, VisaIOError

MODEL_SPECS = {
    "8168D": (1480.0, 1570.0, 0.100),
    "8168E": (1475.0, 1575.0, 0.010),
}
MAX_POWER_W = 1.6e-3
GRID_CHOICES_NM = (0.001, 0.01, 0.1)


def _bits(names):
    def parse(raw):
        try:
            v = int(float(raw))
        except (TypeError, ValueError):
            return None
        on = [n for b, n in names.items() if v & (1 << b)]
        return ", ".join(on) if on else "OK"
    return parse


OPTIONS = (
    Opt("wavelength_nm", "Wavelength", "Wavelength", "number", ":WAVELENGTH?", ":WAVELENGTH {v}", unit="nm",
        scale=1e-9, tip="Snapped to the tuning grid by the Laser page; this field writes exactly what you type"),
    Opt("wl_min_nm", "Programmable minimum", "Wavelength", "number", ":WAVELENGTH? MIN", unit="nm", scale=1e-9),
    Opt("wl_max_nm", "Programmable maximum", "Wavelength", "number", ":WAVELENGTH? MAX", unit="nm", scale=1e-9),
    Opt("wl_ref_nm", "Reference wavelength λ0", "Wavelength", "number", ":WAVELENGTH:REFERENCE?", unit="nm",
        scale=1e-9),
    Opt("wl_ref_set", "Set λ0 = current wavelength", "Wavelength", "action", set=":WAVELENGTH:REFERENCE:DISPLAY"),
    Opt("rel_freq_hz", "Relative frequency (from λ0)", "Wavelength", "number", ":WAVELENGTH:FREQUENCY?",
        ":WAVELENGTH:FREQUENCY {v}", unit="Hz",
        tip="Output = λ0 shifted by this frequency (c/λ = c/λ0 + df)"),
    Opt("power_w", "Power", "Power", "number", ":POWER?", ":POWER {v}W", unit="W", lo=10e-9, hi=MAX_POWER_W),
    Opt("power_max_w", "Maximum power here", "Power", "number", ":POWER? MAX", unit="W"),
    Opt("power_unit", "Front-panel unit", "Power", "choice", ":POWER:UNIT?", ":POWER:UNIT {v}",
        choices=[("dBm", "DBM"), ("W", "W")], parse=lambda r: "W" if str(r).strip() in ("2", "+2", "W") else "DBM"),
    Opt("att_mode", "Attenuator mode (option 003)", "Power", "choice", ":POWER:ATTENUATION:AUTO?",
        ":POWER:ATTENUATION:AUTO {v}", choices=[("power mode", "1"), ("attenuation mode", "0")],
        parse=lambda r: "1" if str(r).strip() in ("1", "+1", "ON") else "0"),
    Opt("att_db", "Attenuation (option 003)", "Power", "number", ":POWER:ATTENUATION?", ":POWER:ATTENUATION {v}DB",
        unit="dB", lo=0, hi=40),
    Opt("att_dark", "Attenuator dark (option 003)", "Power", "bool", ":POWER:ATTENUATION:DARK?",
        ":POWER:ATTENUATION:DARK {v}"),
    Opt("am_state", "Modulation", "Modulation", "bool", ":SOURCE:AM:STATE?", ":SOURCE:AM:STATE {v}"),
    Opt("am_source", "Source", "Modulation", "choice", ":SOURCE:AM:SOURCE?", ":SOURCE:AM:SOURCE {v}",
        choices=[("internal", "0"), ("coherence control (INT2)", "1"), ("external input", "2")],
        parse=lambda r: str(int(float(r))) if r is not None else None),
    Opt("am_freq_hz", "Internal frequency", "Modulation", "number", ":SOURCE:AM:INTERNAL:FREQUENCY?",
        ":SOURCE:AM:INTERNAL:FREQUENCY {v}HZ", unit="Hz", lo=250, hi=300e3),
    Opt("modout", "Modulation output", "Modulation", "choice", ":SOURCE:MODOUT?", ":SOURCE:MODOUT {v}",
        choices=[("always", "0"), ("gated with laser ready", "1")],
        parse=lambda r: "1" if str(r).strip() in ("1", "+1") else "0"),
    Opt("oper_status", "Operation status", "Status", "text", ":STATUS:OPERATION:CONDITION?",
        parse=_bits({8: "power above what the laser can give", 9: "initialising"})),
    Opt("ques_status", "Questionable status", "Status", "text", ":STATUS:QUESTIONABLE:CONDITION?",
        parse=_bits({7: "coherence control uncalibrated", 9: "temperature stabilising",
                     10: "output off to protect the diode"})),
    Opt("lock", "Front-panel lock", "Status", "bool", ":LOCK?"),
    Opt("error", "Error queue", "Status", "text", ":SYSTEM:ERROR?"),
    Opt("display_on", "Display", "System", "bool", ":DISPLAY:ENABLE?", ":DISPLAY:ENABLE {v}"),
    Opt("date", "Date", "System", "text", ":SYSTEM:DATE?"),
    Opt("time", "Time", "System", "text", ":SYSTEM:TIME?"),
    Opt("clear_status", "Clear status (*CLS)", "System", "action", set="*CLS"),
)


class HP8168(Device):
    KIND = "hp8168"
    LABEL = "HP 8168D/E tunable laser"
    RESTORABLE = ("wavelength_nm", "power_w", "am_source", "am_frequency")
    OPTIONS = OPTIONS

    def __init__(self, resource: Optional[str] = None, model: Optional[str] = None,
                 inst=None, timeout_ms: int = 15000):
        super().__init__()
        self.io = VisaInstrument(resource, inst=inst, timeout_ms=timeout_ms)
        self.address = self.io.resource
        self.io.write("*CLS")
        self._idn = self.io.try_query("*IDN?", 3000) or ""
        if model is None:
            model = "8168E" if "8168E" in self._idn.upper() else "8168D"
        self.model = model.upper().replace("HP", "")
        self.wl_min, self.wl_max, self.grid_nm = MODEL_SPECS[self.model]

    def close(self) -> None:
        try:
            self.io.write("*GTL")
        except Exception:
            pass
        self.io.close()

    def safe_state(self) -> None:
        try:
            self.output_off()
        except Exception:
            pass

    # ---- I/O with error-queue checks ------------------------------------------------
    def check_errors(self):
        errs = []
        for _ in range(20):
            r = self.io.try_query(":SYSTEM:ERROR?", 2000)
            if r is None:
                break
            errs.append(r)
            if r.split(",")[0].strip() in ("0", "+0"):
                break
        return errs

    def _write(self, cmd: str, check: bool = True) -> bool:
        self.io.write(cmd)
        if not check:
            return True
        time.sleep(0.05)
        err = self.io.try_query(":SYSTEM:ERROR?", 2000)
        if err is not None and err.split(",")[0].strip() not in ("0", "+0"):
            raise DeviceError(f"HP8168 rejected {cmd!r}: {err}")
        return True

    def _qf(self, cmd: str) -> Optional[float]:
        r = self.io.try_query(cmd, 5000)
        if r is None:
            self.check_errors()
            return None
        try:
            return float(r)
        except ValueError:
            return None

    # ---- identity ------------------------------------------------------------------------
    def identify(self) -> Identity:
        raw = self._idn or self.io.try_query("*IDN?", 3000) or ""
        p = [x.strip() for x in raw.split(",")]
        return Identity(self.KIND, model=p[1] if len(p) > 1 else f"HP{self.model}",
                        serial=p[2] if len(p) > 2 else "", firmware=p[3] if len(p) > 3 else "",
                        raw=raw, extra={"options": self.io.try_query("*OPT?", 3000)})

    def reset(self): self.io.write("*RST"); self.io.write("*CLS"); time.sleep(2)
    def clear(self): self.io.clear(); self.io.write("*CLS")
    def self_test(self): return self.io.try_query("*TST?", 20000)

    def status(self) -> Dict[str, Any]:
        return {"stb": self.io.try_query("*STB?"), "esr": self.io.try_query("*ESR?"),
                "operation_condition": self.io.try_query(":STATUS:OPERATION:CONDITION?")}

    # ---- wavelength -------------------------------------------------------------------------
    def snap(self, wl_nm: float) -> float:
        return round(round(wl_nm / self.grid_nm) * self.grid_nm, 4)

    def set_wavelength_nm(self, wl_nm: float) -> Optional[float]:
        wl_nm = float(wl_nm)
        if not (self.wl_min <= wl_nm <= self.wl_max):
            raise SafetyError(f"{wl_nm:.3f} nm outside HP {self.model} range "
                              f"{self.wl_min}–{self.wl_max} nm")
        wl = self.snap(wl_nm)
        self._write(f":WAVELENGTH {wl * 1e-9:.12f}")
        time.sleep(0.15)
        return self.get_wavelength_nm()

    set_wavelength = set_wavelength_nm

    def get_wavelength_nm(self) -> Optional[float]:
        m = self._qf(":WAVELENGTH?")
        return None if m is None else m * 1e9

    def set_frequency_thz(self, thz: float):
        from laserlock.core.units import thz_to_nm
        return self.set_wavelength_nm(thz_to_nm(thz))

    def step(self, n_steps: int = 1):
        cur = self.get_wavelength_nm()
        if cur is None:
            raise DeviceError("wavelength readback unavailable")
        return self.set_wavelength_nm(cur + n_steps * self.grid_nm)

    # ---- power ---------------------------------------------------------------------------------
    def set_power_w(self, watts: float) -> Optional[float]:
        if not (0 < watts <= MAX_POWER_W):
            raise SafetyError(f"power {watts*1e6:.1f} µW outside 0–{MAX_POWER_W*1e6:.0f} µW")
        self._write(f":POWER {watts:.6e}")
        time.sleep(0.1)
        return self.get_power_w()

    def set_power_dbm(self, dbm: float): return self.set_power_w(dbm_to_w(dbm))
    def set_power_uw(self, uw: float): return self.set_power_w(uw * 1e-6)
    def get_power_w(self) -> Optional[float]: return self._qf(":POWER?")

    # ---- output ---------------------------------------------------------------------------------
    def output_on(self, confirm: bool = True) -> None:
        """Laser current on. (``confirm`` is accepted for older scripts and ignored.)"""
        self._write(":OUTPUT ON")
        time.sleep(0.5)

    def output_off(self) -> None:
        self._write(":OUTPUT OFF")
        time.sleep(0.2)

    def output_is_on(self) -> Optional[bool]:
        r = self.io.try_query(":OUTPUT?")
        return None if r is None else r in ("1", "+1", "ON")

    # ---- amplitude modulation ---------------------------------------------------------------------
    def set_am_source(self, code: int): self._write(f":SOURCE:AM:SOURCE {int(code)}")
    def get_am_source(self): return self.io.try_query(":SOURCE:AM:SOURCE?")
    def set_am_state(self, on: bool): self._write(f":SOURCE:AM:STATE {'ON' if on else 'OFF'}")

    def get_am_state(self) -> Optional[bool]:
        r = self.io.try_query(":SOURCE:AM:STATE?")
        return None if r is None else r in ("1", "+1", "ON")

    def set_am_frequency(self, hz: float): self._write(f":SOURCE:AM:INTERNAL:FREQUENCY {float(hz):.2f}HZ")
    def get_am_frequency(self): return self._qf(":SOURCE:AM:INTERNAL:FREQUENCY?")

    def set_coherence_control(self, on: bool):
        raise DeviceError("Coherence control is front-panel only on this firmware (keep it OFF).")

    # ---- sweep ------------------------------------------------------------------------------------
    def stepped_sweep(self, start_nm, stop_nm, step_nm, dwell_s=0.5, callback=None,
                      stop_event=None, confirm: bool = True):
        """Software step + dwell. Output on at start, always off at the end."""
        step_nm = max(step_nm, self.grid_nm)
        wls = np.arange(start_nm, stop_nm + step_nm / 2, step_nm)
        results = []
        self.output_on(confirm=confirm)
        try:
            for wl in wls:
                if stop_event is not None and stop_event.is_set():
                    break
                actual = self.set_wavelength_nm(wl)
                time.sleep(dwell_s)
                results.append((actual, callback(actual) if callback else None))
        finally:
            self.output_off()
        return results

    # ---- snapshot / poll ----------------------------------------------------------------------------
    def poll(self) -> Dict[str, Any]:
        wl = self.get_wavelength_nm()
        p = self.get_power_w()
        return {"wavelength_nm": wl, "frequency_thz": nm_to_thz(wl) if wl else None,
                "power_w": p, "power_dbm": w_to_dbm(p) if p else None,
                "output_on": self.output_is_on(), "grid_nm": self.grid_nm}

    def snapshot(self) -> Dict[str, Any]:
        d = self.poll()
        d.update({"model": self.model, "am_source": self.get_am_source(),
                  "am_state": self.get_am_state(), "am_frequency": self.get_am_frequency()})
        return d

    def _setter_for(self, key):
        return {"wavelength_nm": self.set_wavelength_nm, "power_w": self.set_power_w,
                "am_source": self.set_am_source, "am_frequency": self.set_am_frequency}.get(key)
