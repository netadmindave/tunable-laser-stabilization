"""HP / Agilent 8563E spectrum analyzer (GPIB, HP proprietary commands).

This unit does not answer *IDN?; identification uses ID? and SER?.
Every trace is 601 points. ``stitched_sweep`` tiles a wide range with
narrow sub-spans to get fine resolution (ported from the notebook, minus
plotting).
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import numpy as np

from laserlock.core.base import Device, DeviceError, Identity, Opt
from laserlock.core.visaio import VisaInstrument

POINTS = 601

_RBW = [1, 3, 10, 30, 100, 300, 1e3, 3e3, 10e3, 30e3, 100e3, 300e3, 1e6, 2e6]
_VBW = [1, 3, 10, 30, 100, 300, 1e3, 3e3, 10e3, 30e3, 100e3, 300e3, 1e6, 3e6]


def _hz_choices(vals):
    from laserlock.core.units import eng
    return [("auto (coupled)", "AUTO")] + [(eng(v, "Hz"), float(v)) for v in vals]


def _scale_get(d):
    r = d.io.try_query("LG?", 3000)
    try:
        return "LIN" if r is not None and float(r) == 0 else ("LOG" if r is not None else None)
    except ValueError:
        return None


def _scale_set(d, v):
    d.set_scale("lin" if v == "LIN" else "log")


OPTIONS = (
    # frequency
    Opt("center_hz", "Center", "Frequency", "number", "CF?", "CF {v}HZ", unit="Hz", lo=0, hi=26.5e9),
    Opt("span_hz", "Span", "Frequency", "number", "SP?", "SP {v}HZ", unit="Hz", lo=0, hi=26.5e9),
    Opt("start_hz", "Start", "Frequency", "number", "FA?", "FA {v}HZ", unit="Hz", lo=0, hi=26.5e9),
    Opt("stop_hz", "Stop", "Frequency", "number", "FB?", "FB {v}HZ", unit="Hz", lo=0, hi=26.5e9),
    Opt("cf_step_hz", "Center step", "Frequency", "number", "SS?", "SS {v}HZ", unit="Hz"),
    Opt("freq_offset_hz", "Frequency offset", "Frequency", "number", "FOFFSET?", "FOFFSET {v}HZ", unit="Hz"),
    Opt("full_span", "Full span", "Frequency", "action", set="FS"),
    # bandwidth
    Opt("rbw_hz", "Resolution BW", "Bandwidth", "choice", "RB?", "RB {v}", choices=_hz_choices(_RBW)),
    Opt("vbw_hz", "Video BW", "Bandwidth", "choice", "VB?", "VB {v}", choices=_hz_choices(_VBW)),
    Opt("vbr", "VBW / RBW ratio", "Bandwidth", "number", "VBR?", "VBR {v}", lo=0.003, hi=3),
    Opt("rbr", "RBW / span ratio", "Bandwidth", "number", "RBR?", "RBR {v}", lo=0.002, hi=0.1),
    Opt("couple_all", "Couple everything (AUTO)", "Bandwidth", "action", set="AUTOCPL"),
    # amplitude
    Opt("scale", "Scale", "Amplitude", "choice", _scale_get, _scale_set,
        choices=[("Log (dBm)", "LOG"), ("Linear (W)", "LIN")],
        tip="LG/LN on the instrument; linear traces come back in watts"),
    Opt("db_per_div", "Log scale", "Amplitude", "choice", "LG?", "LG {v}DB",
        choices=[("1 dB/div", 1.0), ("2 dB/div", 2.0), ("5 dB/div", 5.0), ("10 dB/div", 10.0)]),
    Opt("aunits", "Amplitude units", "Amplitude", "choice", "AUNITS?", "AUNITS {v}",
        choices=[("dBm", "DBM"), ("dBmV", "DBMV"), ("dBµV", "DBUV"), ("V", "V"), ("W", "W")]),
    Opt("ref_level", "Reference level", "Amplitude", "number", "RL?", "RL {v}", tip="in the amplitude units above"),
    Opt("atten_db", "Input attenuation", "Amplitude", "choice", "AT?", "AT {v}",
        choices=[("auto", "AUTO")] + [(f"{a} dB", float(a)) for a in range(0, 80, 10)]),
    Opt("ref_offset_db", "Reference offset", "Amplitude", "number", "ROFFSET?", "ROFFSET {v}DB", unit="dB"),
    Opt("display_line", "Display line", "Amplitude", "number", "DL?", "DL {v}"),
    Opt("threshold", "Threshold", "Amplitude", "number", "TH?", "TH {v}"),
    # sweep
    Opt("sweep_time_s", "Sweep time", "Sweep & trigger", "number", "ST?", "ST {v}SC", unit="s", lo=50e-6, hi=100),
    Opt("sweep_time_auto", "Sweep time auto", "Sweep & trigger", "action", set="ST AUTO"),
    Opt("sweep_mode", "Sweep", "Sweep & trigger", "choice", None, "{v}",
        choices=[("continuous", "CONTS"), ("single", "SNGLS")]),
    Opt("trigger", "Trigger", "Sweep & trigger", "choice", "TM?", "TM {v}",
        choices=[("free run", "FREE"), ("video", "VID"), ("line", "LINE"), ("external", "EXT")]),
    Opt("detector", "Detector", "Sweep & trigger", "choice", "DET?", "DET {v}",
        choices=[("positive peak", "POS"), ("negative peak", "NEG"), ("sample", "SMP"), ("normal", "NRM")]),
    Opt("vavg_count", "Video averages", "Sweep & trigger", "int", "VAVG?", "VAVG {v}", lo=1, hi=999),
    Opt("vavg_on", "Video averaging", "Sweep & trigger", "bool", None, "VAVG {v}"),
    Opt("trace_a", "Trace A mode", "Sweep & trigger", "choice", None, "{v} TRA",
        choices=[("clear-write", "CLRW"), ("max hold", "MXMH"), ("min hold", "MINH"), ("view", "VIEW"),
                 ("blank", "BLANK")]),
    # reference
    Opt("ext_ref", "External 10 MHz reference", "Reference", "bool", "FREF?", "FREF {v}", bools=("EXT", "INT"),
        tip="Rear J9 10 MHz REF IN/OUT. EXT shows an X at the left of the screen."),
    # markers
    Opt("counter_on", "Frequency counter", "Markers", "bool", "MKFC?", "MKFC {v}"),
    Opt("counter_res_hz", "Counter resolution", "Markers", "choice", "MKFCR?", "MKFCR {v}HZ",
        choices=[("1 Hz", 1.0), ("10 Hz", 10.0), ("100 Hz", 100.0), ("1 kHz", 1e3), ("10 kHz", 10e3)]),
    Opt("signal_track", "Signal track", "Markers", "bool", "MKTRACK?", "MKTRACK {v}"),
    Opt("marker_noise", "Marker noise (per Hz)", "Markers", "bool", "MKNOISE?", "MKNOISE {v}"),
    Opt("peak_excursion_db", "Peak excursion", "Markers", "number", "MKPX?", "MKPX {v}DB", unit="dB"),
    Opt("marker_to_cf", "Marker → center", "Markers", "action", set="MKCF"),
    Opt("marker_to_rl", "Marker → reference level", "Markers", "action", set="MKRL"),
    Opt("markers_off", "Markers off", "Markers", "action", set="MKOFF"),
    # system
    Opt("title", "Screen title", "System", "text", None, "TITLE@{v}@"),
    Opt("error", "Error queue", "System", "text", "ERR?"),
    Opt("adjall", "LO & IF adjust (ADJALL)", "System", "action", set="ADJALL"),
    Opt("preset", "Instrument preset (IP)", "System", "action", set="IP"),
)


class HP8563E(Device):
    KIND = "hp8563e"
    LABEL = "HP 8563E spectrum analyzer"
    RESTORABLE = ("center_hz", "span_hz", "ref_dbm", "rbw_hz", "vbw_hz")
    OPTIONS = OPTIONS
    REFERENCE = "ext_ref"

    def __init__(self, resource: Optional[str] = None, inst=None, timeout_ms: int = 30000,
                 sweep_timeout_s: float = 120):
        super().__init__()
        self.io = VisaInstrument(resource, inst=inst, timeout_ms=timeout_ms)
        self.address = self.io.resource
        self.sweep_timeout_s = sweep_timeout_s

    def close(self) -> None:
        try:
            self.io.write("*GTL")
        except Exception:
            pass
        self.io.close()

    def w(self, cmd): self.io.write(cmd)

    def qf(self, cmd) -> Optional[float]:
        return self.io.query_float(cmd)

    # ---- identity ----------------------------------------------------------------------------
    def identify(self) -> Identity:
        reply = (self.io.try_query("ID?", 2000) or "").strip()
        serial = (self.io.try_query("SER?", 2000) or "").strip() if reply else ""
        # raw stays empty when the analyzer didn't answer: the app then reports it instead of "connected"
        return Identity(self.KIND, model=reply or "HP8563E", serial=serial, raw=f"{reply} {serial}".strip())

    fref_keep = True          # re-select the external 10 MHz after a preset (IP sets FREF INT)
    _want_ext = False

    def reset(self):
        self.w("IP")
        time.sleep(2)
        self._restore_fref()

    def _restore_fref(self):
        if self.fref_keep and self._want_ext:
            self.w("FREF EXT")

    def write_option(self, key, value=None, readback=True):
        if key == "ext_ref":
            self._want_ext = bool(value)
        r = super().write_option(key, value, readback)
        if key == "preset":
            time.sleep(2)
            self._restore_fref()
        return r
    def clear(self): self.io.clear()

    # ---- configuration ----------------------------------------------------------------------
    def configure(self, center_hz=None, span_hz=None, ref_dbm=None, rbw_hz=None, vbw_hz=None,
                  atten_db=None, sweep_time_s=None) -> None:
        if center_hz is not None: self.set_center_hz(center_hz)
        if span_hz is not None: self.set_span_hz(span_hz)
        if ref_dbm is not None: self.set_ref_dbm(ref_dbm)
        if rbw_hz is not None: self.set_rbw_hz(rbw_hz)
        if vbw_hz is not None: self.set_vbw_hz(vbw_hz)
        if atten_db is not None:
            self.w("AT AUTO" if str(atten_db).upper() == "AUTO" else f"AT {int(atten_db)} DB")
        if sweep_time_s is not None:
            self.w("ST AUTO" if not sweep_time_s else f"ST {sweep_time_s:.4f} SC")

    def set_center_hz(self, f): self.w(f"CF {float(f):.6e} HZ")
    def set_span_hz(self, f): self.w(f"SP {float(f):.6e} HZ")
    def set_start_stop(self, a, b): self.w(f"FA {a:.6e} HZ"); self.w(f"FB {b:.6e} HZ")
    def set_ref_dbm(self, d): self.w(f"RL {float(d):.1f} DM")
    def set_rbw_hz(self, f): self.w(f"RB {float(f):.6e} HZ")
    def set_vbw_hz(self, f): self.w(f"VB {float(f):.6e} HZ")
    def set_detector(self, mode="POS"): self.w(f"DET {mode}")
    def set_trace_mode(self, mode="CLRW", trace="TRA"): self.w(f"{trace} {mode}")

    def set_averaging(self, count=10, enable=True):
        if enable:
            self.w(f"VAVG {int(count)}")
            self.w("VAVG ON")
        else:
            self.w("VAVG OFF")

    # ---- scale and reference ------------------------------------------------------------------
    def set_scale(self, scale: str = "log", db_per_div: float = 10) -> None:
        """'log' → LG n dB/div with dBm; 'lin' → LN with watts (traces then come back in W)."""
        if str(scale).lower().startswith("lin"):
            self.w("LN")
            self.w("AUNITS W")
        else:
            self.w(f"LG {int(db_per_div)}DB")
            self.w("AUNITS DBM")

    def get_scale(self) -> Optional[str]:
        return {"LIN": "lin", "LOG": "log"}.get(_scale_get(self))

    def amplitude_unit(self) -> str:
        u = (self.io.try_query("AUNITS?", 3000) or "DBM").strip().upper()
        return {"DBM": "dBm", "DBMV": "dBmV", "DBUV": "dBµV", "V": "V", "W": "W"}.get(u, u)

    def set_ext_ref(self, on: bool) -> None:
        self._want_ext = bool(on)
        self.w("FREF EXT" if on else "FREF INT")

    def ext_ref(self) -> Optional[bool]:
        r = self.io.try_query("FREF?", 3000)
        return None if r is None else r.strip().upper().startswith("EXT")

    def settings(self) -> Dict[str, Optional[float]]:
        return {"center_hz": self.qf("CF?"), "span_hz": self.qf("SP?"),
                "start_hz": self.qf("FA?"), "stop_hz": self.qf("FB?"),
                "ref_dbm": self.qf("RL?"), "rbw_hz": self.qf("RB?"), "vbw_hz": self.qf("VB?")}

    # ---- sweeps -------------------------------------------------------------------------------
    def single_sweep(self) -> bool:
        self.w("SNGLS")
        self.w("TS")
        t_end = time.time() + self.sweep_timeout_s
        while time.time() < t_end:
            if (self.io.try_query("DONE?") or "").strip() == "1":
                return True
            time.sleep(0.2)
        return False

    def continuous(self): self.w("CONTS")

    def fetch_trace(self, trace: str = "TRA") -> Tuple[np.ndarray, np.ndarray]:
        fa, fb = self.qf("FA?"), self.qf("FB?")
        raw = self.io.query(f"TDF P; {trace}?")
        amps = np.array([float(v) for v in raw.split(",") if v.strip()])
        return np.linspace(fa, fb, len(amps)), amps

    def sweep_and_fetch(self, trace: str = "TRA"):
        if not self.single_sweep():
            raise DeviceError("8563E sweep timed out")
        return self.fetch_trace(trace)

    # ---- markers ---------------------------------------------------------------------------------
    def peak_search(self) -> Tuple[Optional[float], Optional[float]]:
        self.w("MKPK HI")
        time.sleep(0.1)
        return self.qf("MKF?"), self.qf("MKA?")

    def next_peak(self):
        self.w("MKPK NH")
        time.sleep(0.1)
        return self.qf("MKF?"), self.qf("MKA?")

    def marker_at(self, f_hz: float) -> Optional[float]:
        self.w(f"MKF {f_hz:.6e} HZ")
        time.sleep(0.1)
        return self.qf("MKA?")

    def markers_off(self): self.w("MKOFF")

    # ---- stitched sweep ---------------------------------------------------------------------------
    def stitched_sweep(self, start_hz: float, stop_hz: float, resolution_hz: Optional[float] = None,
                       total_points: Optional[int] = None, rbw_hz=None, vbw_hz=None,
                       stop_event=None, progress=None) -> Dict[str, np.ndarray]:
        if (resolution_hz is None) == (total_points is None):
            raise ValueError("give exactly one of resolution_hz or total_points")
        rng = stop_hz - start_hz
        if total_points is not None:
            resolution_hz = rng / (total_points - 1)
        sub = (POINTS - 1) * resolution_hz
        n = max(1, int(np.ceil(rng / sub)))
        if rbw_hz is not None: self.set_rbw_hz(rbw_hz)
        if vbw_hz is not None: self.set_vbw_hz(vbw_hz)
        fs, ps, seg = [], [], []
        for i in range(n):
            if stop_event is not None and stop_event.is_set():
                break
            a = start_hz + i * sub
            self.set_start_stop(a, a + sub)
            f, p = self.sweep_and_fetch()
            if i > 0:
                f, p = f[1:], p[1:]
            fs.append(f); ps.append(p); seg.append(np.full(len(f), i))
            if progress:
                progress(i + 1, n)
        return {"frequency_hz": np.concatenate(fs), "amplitude_dbm": np.concatenate(ps),
                "sub_span_index": np.concatenate(seg)}

    # ---- snapshot ----------------------------------------------------------------------------------
    def poll(self) -> Dict[str, Any]:
        d = self.settings()
        d["ext_ref"] = self.ext_ref()
        d["scale"] = self.get_scale()
        return d

    def snapshot(self) -> Dict[str, Any]:
        d = self.poll()
        d.update({k: v for k, v in self.read_options().items() if k not in d and not k.startswith("_")})
        return d

    def _setter_for(self, key):
        return {"center_hz": self.set_center_hz, "span_hz": self.set_span_hz,
                "ref_dbm": self.set_ref_dbm, "rbw_hz": self.set_rbw_hz,
                "vbw_hz": self.set_vbw_hz}.get(key)
