"""Rigol MHO5104 oscilloscope (USB-TMC, SCPI).

Ported from rigol_mho5104.ipynb including the hard-won MHO behaviours:

* MATH must use the ``:MATH<n>:`` prefix (bare ``:MATH:`` is not valid).
* FFT span has no SCPI command: span = MDEPth / (timebase × 20).
* Deep-memory reads need STARt/STOP set before POINts (they are coupled) and
  POINts resets after every acquisition, so it is verified before each read.
* V = (raw − YREFerence) × YINCrement + YORigin. WORD keeps all 12 ADC bits.
* Screenshots use query_binary_values (read_raw stops at the USB EOM bit).
* 50 Ω input tops out at 1 V/div.
"""
from __future__ import annotations

import io
import math
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from laserlock.core.base import Device, DeviceError, Identity, Opt
from laserlock.core.units import ceil_125, eng, first_125_below, seq_125, snap_125
from laserlock.core.visaio import VisaInstrument, VisaIOError

MEAS_ITEMS = {
    "vmax": "VMAX", "vmin": "VMIN", "vamp": "VAMP", "vtop": "VTOP", "vbase": "VBASE",
    "vavg": "VAVG", "vrms": "VRMS", "period": "PERiod", "frequency": "FREQuency",
    "rise_time": "RTIMe", "fall_time": "FTIMe", "pos_width": "PWIDth", "neg_width": "NWIDth",
    "pos_duty": "PDUT", "neg_duty": "NDUT", "overshoot": "OVERshoot", "preshoot": "PREShoot",
    "neg_edges": "NEDG",
}
MEAS_INVALID = 9.9e37
#: memory depths offered in the GUI (the notebook's Nyquist helper used the first four;
#: the long-term monitor confirmed 5 M–50 M on this unit)
MEMORY_DEPTHS = (1_000, 10_000, 100_000, 1_000_000, 5_000_000, 10_000_000,
                 25_000_000, 50_000_000, 100_000_000, 125_000_000, 200_000_000, 250_000_000, 500_000_000)
#: coarse (1-2-5) vertical and horizontal steps from the MHO/DHO5000 user guide
VOLTS_PER_DIV = tuple(seq_125(100e-6, 10.0))
SECONDS_PER_DIV = tuple(seq_125(200e-12, 500.0))
AVERAGES = tuple(2 ** k for k in range(1, 17))


def _depth_label(d):
    return "auto" if d == "AUTO" else (f"{d / 1e6:g} Mpts" if d >= 1e6 else f"{d / 1e3:g} kpts")


def _ch_options(n: int):
    c = f":CHANnel{n}"
    g = f"Channel {n}"
    return [
        Opt(f"ch{n}_display", "Display", g, "bool", f"{c}:DISPlay?", f"{c}:DISPlay {{v}}"),
        Opt(f"ch{n}_scale", "Scale", g, "choice", f"{c}:SCALe?", f"{c}:SCALe {{v}}",
            choices=[(eng(x, "V") + "/div", x) for x in VOLTS_PER_DIV], tip="1-2-5 coarse steps; tick Fine for any value"),
        Opt(f"ch{n}_vernier", "Fine (vernier) scale", g, "bool", f"{c}:VERNier?", f"{c}:VERNier {{v}}"),
        Opt(f"ch{n}_offset", "Offset", g, "number", f"{c}:OFFSet?", f"{c}:OFFSet {{v}}", unit="V"),
        Opt(f"ch{n}_coupling", "Coupling", g, "choice", f"{c}:COUPling?", f"{c}:COUPling {{v}}",
            choices=["DC", "AC", "GND"]),
        Opt(f"ch{n}_impedance", "Input", g, "choice", f"{c}:IMPedance?", f"{c}:IMPedance {{v}}",
            choices=[("1 MΩ", "OMEG"), ("50 Ω (≤ 1 V/div)", "FIFT")]),
        Opt(f"ch{n}_bwlimit", "Bandwidth limit", g, "choice", f"{c}:BWLimit?", f"{c}:BWLimit {{v}}",
            choices=[("off", "OFF"), ("20 MHz", "20M"), ("100 MHz", "100M"), ("200 MHz", "200M")]),
        Opt(f"ch{n}_probe", "Probe ratio", g, "choice", f"{c}:PROBe?", f"{c}:PROBe {{v}}",
            choices=[(f"{x:g}×", float(x)) for x in (0.01, 0.1, 1, 2, 5, 10, 20, 50, 100, 1000)]),
        Opt(f"ch{n}_invert", "Invert", g, "bool", f"{c}:INVert?", f"{c}:INVert {{v}}"),
        Opt(f"ch{n}_unit", "Unit", g, "choice", f"{c}:UNITs?", f"{c}:UNITs {{v}}",
            choices=[("V", "VOLT"), ("W", "WATT"), ("A", "AMP"), ("U", "UNKN")]),
        Opt(f"ch{n}_label", "Label", g, "text", f"{c}:LABel:CONTent?", f'{c}:LABel:CONTent "{{v}}"'),
    ]


def build_options():
    opts = [
        Opt("ext_ref", "External 10 MHz reference (rear REF IN)", "Reference", "bool", lambda d: d.ext_ref(),
            lambda d, v: d.set_ext_ref(bool(v)),
            tip="CINP = lock to the 10 MHz on the rear BNC, COUT = output the internal 10 MHz there. "
                "Utility → Other → EXT 10M IN. Command from the MHO/DHO5000 programming "
                                      "guide (§3.30.5 :SYSTem:RCLock)."),
        Opt("ref_clock", "Rear 10 MHz BNC", "Reference", "choice", ":SYSTem:RCLock?", lambda d, v: d.set_ref_clock(v),
            choices=[("input (use GPS 10 MHz)", "CINP"), ("output (internal 10 MHz)", "COUT"), ("off", "OFF")]),
        Opt("tb_scale", "Time / div", "Timebase", "choice", ":TIMebase:MAIN:SCALe?", ":TIMebase:MAIN:SCALe {v}",
            choices=[(eng(x, "s") + "/div", x) for x in SECONDS_PER_DIV]),
        Opt("tb_offset", "Position (offset)", "Timebase", "number", ":TIMebase:MAIN:OFFSet?",
            ":TIMebase:MAIN:OFFSet {v}", unit="s"),
        Opt("tb_mode", "Mode", "Timebase", "choice", ":TIMebase:MODE?", ":TIMebase:MODE {v}",
            choices=[("Y-T", "MAIN"), ("X-Y", "XY"), ("roll", "ROLL")]),
        Opt("tb_fine", "Fine (vernier) time base", "Timebase", "bool", ":TIMebase:VERNier?", ":TIMebase:VERNier {v}"),
        Opt("tb_delay", "Zoom (delayed sweep)", "Timebase", "bool", ":TIMebase:DELay:ENABle?",
            ":TIMebase:DELay:ENABle {v}"),
        Opt("tb_delay_scale", "Zoom time / div", "Timebase", "choice", ":TIMebase:DELay:SCALe?",
            ":TIMebase:DELay:SCALe {v}", choices=[(eng(x, "s") + "/div", x) for x in SECONDS_PER_DIV]),
        Opt("acq_type", "Acquisition", "Acquire", "choice", ":ACQuire:TYPE?", ":ACQuire:TYPE {v}",
            choices=[("normal", "NORM"), ("average", "AVER"), ("peak detect", "PEAK"), ("high resolution", "HRES"),
                     ("ultra acquire", "ULTR")]),
        Opt("acq_averages", "Averages", "Acquire", "choice", ":ACQuire:AVERages?", ":ACQuire:AVERages {v}",
            choices=[(str(a), float(a)) for a in AVERAGES]),
        Opt("acq_mdepth", "Memory depth", "Acquire", "choice", ":ACQuire:MDEPth?", ":ACQuire:MDEPth {v}",
            choices=[("auto", "AUTO")] + [(_depth_label(d), float(d)) for d in MEMORY_DEPTHS]),
        Opt("acq_srate", "Sample rate", "Acquire", "number", ":ACQuire:SRATe?", unit="Sa/s"),
        Opt("trig_mode", "Trigger type", "Trigger", "choice", ":TRIGger:MODE?", ":TRIGger:MODE {v}",
            choices=[("edge", "EDGE"), ("pulse", "PULS"), ("slope", "SLOP"), ("video", "VID"), ("pattern", "PATT"),
                     ("duration", "DUR"), ("timeout", "TIM"), ("runt", "RUNT"), ("window", "WIND"),
                     ("delay", "DEL"), ("setup/hold", "SHOL"), ("Nth edge", "NEDG")]),
        Opt("trig_sweep", "Sweep", "Trigger", "choice", ":TRIGger:SWEep?", ":TRIGger:SWEep {v}",
            choices=[("auto", "AUTO"), ("normal", "NORM"), ("single", "SING")]),
        Opt("trig_source", "Edge source", "Trigger", "choice", ":TRIGger:EDGE:SOURce?", ":TRIGger:EDGE:SOURce {v}",
            choices=["CHAN1", "CHAN2", "CHAN3", "CHAN4", "EXT", "ACL"]),
        Opt("trig_slope", "Edge slope", "Trigger", "choice", ":TRIGger:EDGE:SLOPe?", ":TRIGger:EDGE:SLOPe {v}",
            choices=[("rising", "POS"), ("falling", "NEG"), ("either", "RFAL")]),
        Opt("trig_level", "Edge level", "Trigger", "number", ":TRIGger:EDGE:LEVel?", ":TRIGger:EDGE:LEVel {v}",
            unit="V"),
        Opt("trig_coupling", "Coupling", "Trigger", "choice", ":TRIGger:COUPling?", ":TRIGger:COUPling {v}",
            choices=[("DC", "DC"), ("AC", "AC"), ("LF reject", "LFR"), ("HF reject", "HFR")]),
        Opt("trig_holdoff", "Holdoff", "Trigger", "number", ":TRIGger:HOLDoff?", ":TRIGger:HOLDoff {v}", unit="s"),
        Opt("trig_nreject", "Noise reject", "Trigger", "bool", ":TRIGger:NREJect?", ":TRIGger:NREJect {v}"),
        Opt("disp_grid", "Grid", "Display", "choice", ":DISPlay:GRID?", ":DISPlay:GRID {v}",
            choices=[("full", "FULL"), ("half", "HALF"), ("none", "NONE")]),
        Opt("disp_brightness", "Waveform brightness", "Display", "int", ":DISPlay:WBRightness?",
            ":DISPlay:WBRightness {v}", unit="%", lo=1, hi=100),
        Opt("disp_persist", "Persistence", "Display", "choice", ":DISPlay:GRADing:TIME?", ":DISPlay:GRADing:TIME {v}",
            choices=[("minimum", "MIN"), ("100 ms", "0.1"), ("200 ms", "0.2"), ("500 ms", "0.5"), ("1 s", "1"),
                     ("5 s", "5"), ("10 s", "10"), ("infinite", "INF")]),
        Opt("disp_clear", "Clear display", "Display", "action", set=":CLEar"),
        Opt("beeper", "Beeper", "System", "bool", ":SYSTem:BEEPer?", ":SYSTem:BEEPer {v}"),
        Opt("error", "Error queue", "System", "text", ":SYSTem:ERRor?"),
        Opt("autoscale", "Auto (autoscale)", "System", "action", set=":AUToscale"),
        Opt("reset", "Factory reset (*RST)", "System", "action", set="*RST"),
    ]
    for n in range(1, 5):
        opts += _ch_options(n)
    return opts

MAX_SAMPLE_RATE = 4e9
SCREEN_DIVISIONS = 10
VISA_CHUNK = 102_400   # measured optimum on this unit


class RigolMHO5104(Device):
    KIND = "rigol_mho5104"
    LABEL = "Rigol MHO5104"
    RESTORABLE = ("timebase_scale", "timebase_offset", "acquire_type", "memory_depth")
    OPTIONS = tuple(build_options())
    REFERENCE = "ext_ref"

    def __init__(self, resource: Optional[str] = None, inst=None, timeout_ms: int = 5000):
        super().__init__()
        self.io = VisaInstrument(resource, inst=inst, timeout_ms=timeout_ms)
        self.address = self.io.resource
        try:
            self.io.inst.chunk_size = VISA_CHUNK
        except Exception:
            pass
        self._open_clear()
        self._read_strategy: Optional[str] = None
        self._bad = set()                  # query headers this scope rejected: never sent again
        self._ext_ref: Optional[bool] = None

    def close(self) -> None:
        self.io.close()

    def _open_clear(self) -> None:
        """Device clear, then *CLS, retried once. A session left mid-transfer (app closed during a capture,
        another program's half-read reply) otherwise fails the first write — on Keysight/IVI VISA that can
        show up as VI_ERROR_NCIC or a timeout instead of a clear error."""
        last = None
        for attempt in range(2):
            try:
                self.io.inst.clear()
            except Exception:
                pass
            try:
                self.io.write("*CLS")
                return
            except Exception as e:
                last = e
                time.sleep(0.5)
        raise last

    # ---- helpers ---------------------------------------------------------------------
    # Every helper below is one transaction under the VISA lock: the beat check, the live spectrum,
    # the screen mirror and the poll run on different threads, and an error-queue read must never be
    # answered with another thread's reply (that mis-alignment is what hung the link).
    def recover(self) -> None:
        with self.io.lock:
            self._recover_unlocked()

    def w(self, cmd: str, quiet: bool = False) -> Optional[str]:
        with self.io.lock:
            return self._w_unlocked(cmd, quiet)

    def q(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[str]:
        with self.io.lock:
            return self._q_unlocked(cmd, timeout_ms)

    def _recover_unlocked(self) -> None:
        """Device clear + *CLS: drops a half-read reply so the next query lines up again."""
        try:
            self.io.inst.clear()
        except Exception:
            pass
        try:
            self.io.inst.read_termination = "\n"
            self.io.write("*CLS")
        except Exception:
            pass

    def _w_unlocked(self, cmd: str, quiet: bool = False) -> Optional[str]:
        """Write, then check the error queue: a rejected command is logged by name (Logs window,
        filter "rigol") and the error is cleared, so the scope doesn't keep showing it.
        Returns the error text, or None when the scope accepted it."""
        self.io.write(cmd)
        if cmd.startswith("*"):
            return None
        err = self.io.try_query(":SYSTem:ERRor?", 1000)
        if err is not None and not err.strip().startswith(("0", "+0")):
            try:
                self.io.write("*CLS")
            except Exception:
                pass
            if not quiet:
                import logging
                logging.getLogger("rigol").warning(f"MHO5104 rejected write {cmd!r}: {err.strip()}")
            return err.strip()
        return None

    def _set_if(self, query: str, cmd: str, accept: Iterable[str]) -> None:
        """Write ``cmd`` only when ``query`` doesn't already give one of ``accept``; raise if rejected."""
        cur = (self.q(query) or "").strip().upper()
        if cur in {a.upper() for a in accept}:
            return
        err = self.w(cmd)
        if err:
            raise DeviceError(f"scope rejected {cmd} ({err})")

    def _wait_stopped(self, timeout: float = 1.5) -> None:
        """:STOP, then wait until the scope reports STOP (waveform settings are refused while running)."""
        st = (self.q(":TRIGger:STATus?") or "").upper()
        if st.startswith("STOP"):
            return
        self.w(":STOP")
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(0.05)
            if (self.q(":TRIGger:STATus?") or "").upper().startswith("STOP"):
                return
        time.sleep(0.1)

    def _require_channel(self, ch: int) -> None:
        """The scope refuses :WAVeform:SOURce for a channel that isn't displayed."""
        r = (self.q(f":CHANnel{int(ch)}:DISPlay?") or "").strip().upper()
        if r in ("0", "OFF"):
            raise DeviceError(f"CH{ch} is off on the scope; turn it on (or pick another scope channel)")

    def option_write(self, cmd: str) -> None:
        self.w(cmd)

    def _q_unlocked(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[str]:
        """Query; a command the scope rejects (it shows "remote ctrl error") is logged, the error is
        cleared and that query is never sent again this session."""
        head = cmd.split()[0].upper()
        if head in self._bad:
            return None
        r = self.io.try_query(cmd, timeout_ms or 2000)
        if r is not None and r.strip() == "":           # MHO answers a rejected query with an empty line
            err = self.io.try_query(":SYSTem:ERRor?", 1000) or ""
            if not err.strip().startswith(("0", "+0")):
                r = None
            else:
                return r
            self._bad.add(head)
            try:
                self.io.write("*CLS")
            except Exception:
                pass
            import logging
            logging.getLogger("rigol").warning(f"MHO5104 rejected {cmd!r} ({err.strip()}); "
                                               "query disabled for this session")
            return None
        if r is None:                                     # timeout: clear the link, don't blacklist
            self.recover()
            err = self.io.try_query(":SYSTem:ERRor?", 1000)
            if err is None or err.strip().startswith(("0", "+0")):
                import logging
                logging.getLogger("rigol").warning(f"MHO5104 timed out on {cmd!r}; link cleared")
                return None
            self._bad.add(head)
            try:
                self.io.write("*CLS")
            except Exception:
                pass
            import logging
            logging.getLogger("rigol").warning(f"MHO5104 did not answer {cmd!r} (error queue: {err}); "
                                               "query disabled for this session")
        return r

    def qf(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[float]:
        r = self.q(cmd, timeout_ms)
        try:
            return None if r is None else float(r)
        except ValueError:
            return None

    def option_query(self, cmd: str) -> Optional[str]:
        return self.q(cmd)

    def check_errors(self) -> List[str]:
        errs = []
        for _ in range(20):
            r = self.q(":SYSTem:ERRor?", 2000)
            if r is None:
                break
            if r.split(",")[0].strip() not in ("0", "+0"):
                errs.append(r)
            else:
                break
        return errs

    # ---- identity / system ---------------------------------------------------------------
    def identify(self) -> Identity:
        raw = self.q("*IDN?") or ""
        p = [x.strip() for x in raw.split(",")]
        return Identity(self.KIND, model=p[1] if len(p) > 1 else "MHO5104",
                        serial=p[2] if len(p) > 2 else "", firmware=p[3] if len(p) > 3 else "",
                        raw=raw)

    def reset(self): self.w("*RST"); self.w("*CLS"); time.sleep(3)
    def run(self): self.w(":RUN")
    def stop(self): self.w(":STOP")
    def single(self): self.w(":SINGle")
    def autoscale(self):
        """MHO5000: :AUToset (:AUToscale is not defined on this series)."""
        if getattr(self, "_no_auto", False):
            raise DeviceError("Auto is not accepted over remote by this scope; use the front-panel AUTO key")
        err = self.w(":AUToset")
        if err:
            self._no_auto = True
            raise DeviceError(f"scope rejected :AUToset ({err}); use the front-panel AUTO key")
        time.sleep(3)
    def clear_display(self): self.w(":CLEar")
    def force_trigger(self): self.w(":TRIGger:FORCe")
    def trigger_status(self) -> Optional[str]: return self.q(":TRIGger:STATus?")

    def status(self) -> Dict[str, Any]:
        return {"stb": self.q("*STB?"), "esr": self.q("*ESR?"),
                "trigger_status": self.trigger_status()}

    def wait_trigger(self, timeout_s: float = 10) -> Optional[str]:
        t_end = time.time() + timeout_s
        while time.time() < t_end:
            st = self.trigger_status()
            if st in ("TD", "STOP"):
                return st
            time.sleep(0.1)
        return None

    def arm_and_wait(self, timeout_s: float = 20) -> bool:
        """:SINGle, then require the status to LEAVE stop before waiting for it."""
        self.single()
        t0 = time.time()
        armed = False
        while time.time() - t0 < timeout_s:
            st = self.trigger_status()
            if not armed:
                if st in ("WAIT", "RUN", "AUTO", "TD"):
                    armed = True
            elif st in ("STOP", "TD"):
                time.sleep(0.05)
                return True
            time.sleep(0.02)
        time.sleep(0.3)
        return self.trigger_status() in ("STOP", "TD")

    # ---- timebase ----------------------------------------------------------------------------
    def set_timebase(self, scale_s: float, offset_s: float = 0.0, mode: str = "MAIN") -> None:
        self.w(f":TIMebase:MODE {mode}")
        self.w(f":TIMebase:MAIN:SCALe {scale_s:.10e}")
        self.w(f":TIMebase:MAIN:OFFSet {offset_s:.6e}")

    def set_timebase_scale(self, scale_s): self.w(f":TIMebase:MAIN:SCALe {float(scale_s):.10e}")
    def set_timebase_offset(self, off_s): self.w(f":TIMebase:MAIN:OFFSet {float(off_s):.6e}")

    def get_timebase(self) -> Dict[str, Any]:
        return {"scale_s": self.qf(":TIMebase:MAIN:SCALe?"),
                "offset_s": self.qf(":TIMebase:MAIN:OFFSet?"),
                "mode": self.q(":TIMebase:MODE?")}

    # ---- channels --------------------------------------------------------------------------------
    def channel_display(self, n: int, on: bool) -> None:
        self.w(f":CHANnel{n}:DISPlay {'ON' if on else 'OFF'}")

    def set_channel(self, n: int, scale_v: Optional[float] = None, offset_v: Optional[float] = None,
                    coupling: Optional[str] = None, bwlimit: Optional[str] = None,
                    probe: Optional[float] = None, impedance: Optional[str] = None,
                    unit: Optional[str] = None, invert: Optional[bool] = None,
                    display: Optional[bool] = None) -> None:
        c = f":CHANnel{n}"
        if display is not None: self.w(f"{c}:DISPlay {'ON' if display else 'OFF'}")
        if impedance is not None: self.w(f"{c}:IMPedance {impedance}")
        if scale_v is not None:
            if (impedance or self.q(f"{c}:IMPedance?") or "") .upper().startswith("FIFT"):
                scale_v = min(scale_v, 1.0)   # 50 Ω range tops out at 1 V/div
            self.w(f"{c}:SCALe {scale_v:.6e}")
        if offset_v is not None: self.w(f"{c}:OFFSet {offset_v:.6e}")
        if coupling is not None: self.w(f"{c}:COUPling {coupling}")
        if bwlimit is not None: self.w(f"{c}:BWLimit {bwlimit}")
        if probe is not None: self.w(f"{c}:PROBe {probe}")
        if unit is not None: self.w(f"{c}:UNIT {unit}")
        if invert is not None: self.w(f"{c}:INVert {'ON' if invert else 'OFF'}")

    def get_channel(self, n: int) -> Dict[str, Any]:
        c = f":CHANnel{n}"
        return {"display": self.q(f"{c}:DISPlay?") in ("1", "ON"),
                "scale_v": self.qf(f"{c}:SCALe?"), "offset_v": self.qf(f"{c}:OFFSet?"),
                "coupling": self.q(f"{c}:COUPling?"), "bwlimit": self.q(f"{c}:BWLimit?"),
                "probe": self.qf(f"{c}:PROBe?"), "impedance": self.q(f"{c}:IMPedance?"),
                "unit": self.q(f"{c}:UNIT?"), "invert": self.q(f"{c}:INVert?")}

    def get_all_channels(self) -> Dict[int, Dict[str, Any]]:
        return {n: self.get_channel(n) for n in range(1, 5)}

    # ---- acquire ------------------------------------------------------------------------------------
    def set_acquire(self, acq_type: str = "NORM", averages: int = 4,
                    mdepth: Optional[int] = None) -> None:
        self.w(f":ACQuire:TYPE {acq_type}")
        if acq_type == "AVER":
            self.w(f":ACQuire:AVERages {int(averages)}")
        if mdepth is not None:
            self.w(f":ACQuire:MDEPth {int(mdepth)}")

    def set_acquire_type(self, t): self.w(f":ACQuire:TYPE {t}")
    def set_memory_depth(self, n): self.w(f":ACQuire:MDEPth {int(n)}")

    def get_acquire(self) -> Dict[str, Any]:
        md = self.q(":ACQuire:MDEPth?")
        try:
            mdv = int(float(md)) if md else None
        except ValueError:                     # "AUTO"
            mdv = md
        return {"type": self.q(":ACQuire:TYPE?"), "averages": self.q(":ACQuire:AVERages?"),
                "mdepth": mdv, "srate": self.qf(":ACQuire:SRATe?")}

    # ---- trigger --------------------------------------------------------------------------------------
    def set_trigger_edge(self, source="CHAN1", slope="POS", level_v=0.0, sweep="AUTO",
                         coupling="DC", holdoff_s=8e-9) -> None:
        self.w(":TRIGger:MODE EDGE")
        self.w(f":TRIGger:SWEep {sweep}")
        self.w(f":TRIGger:COUPling {coupling}")
        self.w(f":TRIGger:HOLDoff {holdoff_s:.6e}")
        self.w(f":TRIGger:EDGe:SOURce {source}")
        self.w(f":TRIGger:EDGe:SLOPe {slope}")
        self.w(f":TRIGger:EDGe:LEVel {level_v:.6e}")

    def set_trigger_pulse(self, source="CHAN1", when="GRE", width_s=1e-6, level_v=0.0, sweep="AUTO"):
        self.w(":TRIGger:MODE PULSe")
        self.w(f":TRIGger:SWEep {sweep}")
        self.w(f":TRIGger:PULSe:SOURce {source}")
        self.w(f":TRIGger:PULSe:WHEN {when}")
        self.w(f":TRIGger:PULSe:WIDTh {width_s:.6e}")
        self.w(f":TRIGger:PULSe:LEVel {level_v:.6e}")

    def get_trigger(self) -> Dict[str, Any]:
        return {k: self.q(c) for k, c in (
            ("mode", ":TRIGger:MODE?"), ("sweep", ":TRIGger:SWEep?"),
            ("status", ":TRIGger:STATus?"), ("coupling", ":TRIGger:COUPling?"),
            ("holdoff", ":TRIGger:HOLDoff?"), ("source", ":TRIGger:EDGe:SOURce?"),
            ("slope", ":TRIGger:EDGe:SLOPe?"), ("level", ":TRIGger:EDGe:LEVel?"))}

    # ---- measurements -----------------------------------------------------------------------------------
    def measure(self, item: str, channel: int = 1) -> float:
        mnem = MEAS_ITEMS.get(item, item)
        raw = self.q(f":MEASure:ITEM? {mnem},CHANnel{channel}")
        if raw is None:
            return float("nan")
        try:
            v = float(raw)
        except ValueError:
            return float("nan")
        return float("nan") if v >= MEAS_INVALID * 0.9 else v

    def measure_all(self, channel: int = 1, items: Optional[Iterable[str]] = None) -> Dict[str, float]:
        return {k: self.measure(k, channel) for k in (items or MEAS_ITEMS)}

    # ---- waveform read ---------------------------------------------------------------------------------
    def read_preamble(self) -> Dict[str, Any]:
        p = [float(x) for x in (self.q(":WAVeform:PREamble?") or "").split(",")]
        if len(p) < 10:
            raise DeviceError("bad waveform preamble")
        return dict(format=p[0], type=p[1], points=int(p[2]), count=int(p[3]),
                    xincrement=p[4], xorigin=p[5], xreference=p[6],
                    yincrement=p[7], yorigin=p[8], yreference=p[9])

    def screen_capture(self, channels: Iterable[int]) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """What the screen shows right now (:WAVeform:MODE NORMal, BYTE): small, quick, and the scope
        keeps running. Returns {channel: (t_s, v_V)}."""
        out = {}
        with self.io.lock:
            try:
                for ch in channels:
                    self._require_channel(ch)
                    self._set_if(":WAVeform:SOURce?", f":WAVeform:SOURce CHANnel{ch}", (f"CHAN{ch}", f"CHANNEL{ch}"))
                    self._set_if(":WAVeform:MODE?", ":WAVeform:MODE NORMal", ("NORM", "NORMAL"))
                    self._set_if(":WAVeform:FORMat?", ":WAVeform:FORMat BYTE", ("BYTE",))
                    pre = self.read_preamble()
                    raw = np.asarray(self._read_block("B"), dtype=np.float64)
                    v = (raw - pre["yreference"]) * pre["yincrement"] + pre["yorigin"]
                    tt = pre["xorigin"] + np.arange(len(v)) * pre["xincrement"]
                    out[int(ch)] = (tt, v)
            except Exception:
                self.recover()                     # never leave a half-read block in the link
                raise
        return out

    def _prepare(self, channel: int, npts: int, fmt: str, tries: int = 3, settle: float = 0.12):
        """Stop (and wait for STOP), then set only what differs; keeps the scope's current
        BYTE/WORD format. Returns (preamble, format)."""
        self._require_channel(channel)
        self._wait_stopped()
        self._set_if(":WAVeform:SOURce?", f":WAVeform:SOURce CHANnel{channel}",
                     (f"CHAN{channel}", f"CHANNEL{channel}"))
        self._set_if(":WAVeform:MODE?", ":WAVeform:MODE MAXimum", ("MAX", "MAXIMUM"))
        cur = (self.q(":WAVeform:FORMat?") or "").strip().upper()
        if cur in ("BYTE", "WORD"):
            fmt = cur
        else:
            self._set_if(":WAVeform:FORMat?", f":WAVeform:FORMat {fmt}", (fmt,))
        got = -1
        for attempt in range(tries):
            for c in (":WAVeform:STARt 1", f":WAVeform:STOP {int(npts)}", f":WAVeform:POINts {int(npts)}"):
                err = self.w(c)
                if err:
                    raise DeviceError(f"scope rejected {c} ({err})")
            time.sleep(settle * (attempt + 1))
            try:
                got = int(float(self.q(":WAVeform:POINts?") or -1))
            except ValueError:
                got = -1
            if got == int(npts):
                return self.read_preamble(), fmt
        raise DeviceError(f"deep-memory read not armed (POINts={got}, wanted {npts})")

    def _read_block(self, datatype: str):
        inst = self.io.inst
        old_term = getattr(inst, "read_termination", None)
        try:
            inst.read_termination = None
        except Exception:
            pass
        try:
            return self.io.query_binary_values(":WAVeform:DATA?", datatype=datatype,
                                               is_big_endian=False, container=np.array,
                                               chunk_size=VISA_CHUNK)
        finally:
            try:
                inst.read_termination = old_term
            except Exception:
                pass

    CAPTURE_MAX_POINTS = 1_000_000

    def capture(self, channel: int = 1, max_points: Optional[int] = None):
        """Generic "scope" capability: CH<n> -> (t_s, v_V); leaves the scope running.
        At most ``max_points`` (1 M by default) so a deep memory setting can't stall the link."""
        md = self.get_acquire().get("mdepth") or 10_000
        n = int(min(md, max_points or self.CAPTURE_MAX_POINTS))
        t, v, _ = self.capture_waveform(channel, points=n, resume=True)
        return t, v

    def capture_waveform(self, channel: int = 1, points: Optional[int] = None,
                         fmt: str = "WORD", chunk_points: int = 1_000_000,
                         resume: bool = False) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Read CH<n> from deep memory. Returns (t_s, v_V, preamble).

        ``points`` defaults to the full memory depth. Large records are read in
        STARt/STOP chunks. ``resume`` puts the scope back in RUN afterwards."""
        codes = {"BYTE": ("B", np.uint8), "WORD": ("H", np.uint16)}
        if points is None:
            points = self.get_acquire()["mdepth"] or 10_000
        npts = int(points)
        with self.io.lock:
            try:
                pre, fmt = self._prepare(channel, npts, fmt.upper())
                dt_code = codes[fmt]
            except Exception:
                self.recover()
                raise
            try:
                if npts <= chunk_points:
                    raw = self._read_block(dt_code[0])
                else:
                    raw = np.empty(npts, dtype=dt_code[1])
                    pos = 0
                    while pos < npts:
                        n = min(chunk_points, npts - pos)
                        self.w(f":WAVeform:STARt {pos + 1}")
                        self.w(f":WAVeform:STOP {pos + n}")
                        time.sleep(0.02)
                        blk = self._read_block(dt_code[0])
                        if len(blk) != n:
                            raise DeviceError(f"chunk at {pos}: got {len(blk)}, expected {n}")
                        raw[pos:pos + n] = blk
                        pos += n
                raw = np.asarray(raw)
                v = (raw.astype(np.float64) - pre["yreference"]) * pre["yincrement"] + pre["yorigin"]
                t = pre["xorigin"] + pre["xincrement"] * np.arange(len(v))
                pre["channel"] = channel
                pre["format"] = fmt.upper()
                return t, v, pre
            finally:
                if resume:
                    self.run()

    def capture_channels(self, channels: Iterable[int], points: Optional[int] = None,
                         fmt: str = "WORD") -> Dict[str, np.ndarray]:
        """Capture several channels from ONE stopped acquisition (shared time axis)."""
        out: Dict[str, np.ndarray] = {}
        for ch in channels:
            t, v, _ = self.capture_waveform(ch, points, fmt)
            out.setdefault("time_s", t)
            out[f"ch{ch}_V"] = v
        self.run()
        return out

    def save_waveform(self, path: str, channels: Iterable[int] = (1,), points: Optional[int] = None,
                      fmt: str = "WORD") -> str:
        from laserlock.datafile import write_csv
        data = self.capture_channels(channels, points, fmt)
        keys = list(data)
        meta = {"scope_timebase": self.get_timebase(), "scope_acquire": self.get_acquire(),
                "scope_channels": {n: self.get_channel(n) for n in channels}, "scope_ext_ref": self.ext_ref()}
        return write_csv(path, keys, columns=[data[k] for k in keys], kind="Rigol MHO5104 waveform", meta=meta)

    # ---- screenshot -------------------------------------------------------------------------------
    def screenshot_bytes(self) -> bytes:
        """Returns PNG bytes (BMP if Pillow is missing)."""
        old = self.io.inst.timeout
        self.io.set_timeout(60000)
        try:
            bmp = bytes(self.io.query_binary_values(":DISPlay:DATA?", datatype="B",
                                                    is_big_endian=False, container=bytearray,
                                                    chunk_size=1024 * 1024))
        finally:
            self.io.set_timeout(old)
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(bmp))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
        except ImportError:
            return bmp

    def screenshot(self, path: str) -> str:
        data = self.screenshot_bytes()
        with open(path, "wb") as f:
            f.write(data)
        return path

    # ---- math -----------------------------------------------------------------------------------------
    def set_math(self, math_n=1, operator="ADD", source1="CHAN1", source2="CHAN2", scale=1.0,
                 offset=0.0, display=True, fft_center_hz=None, fft_window="HANN", fft_unit="DB"):
        m = f":MATH{math_n}"
        self.w(f"{m}:DISPlay {'ON' if display else 'OFF'}")
        self.w(f"{m}:OPERator {operator}")
        self.w(f"{m}:SOURce1 {source1}")
        if operator == "FFT":
            self.w(f"{m}:FFT:SOURce {source1}")
            self.w(f"{m}:FFT:WINDow {fft_window}")
            self.w(f"{m}:FFT:UNIT {fft_unit}")
            if fft_center_hz is not None:
                self.w(f"{m}:FFT:HCEN {fft_center_hz:.6e}")
        else:
            self.w(f"{m}:SOURce2 {source2}")
            self.w(f"{m}:SCALe {scale:.6e}")
            self.w(f"{m}:OFFSet {offset:.6e}")
        return self.check_errors()

    def set_math_fft_center(self, math_n: int, center_hz: float):
        self.w(f":MATH{math_n}:FFT:HCEN {center_hz:.6e}")

    def set_math_fft_span(self, span_hz: float, mdepth: Optional[int] = None) -> Dict[str, float]:
        """FFT span = MDEPth / (timebase × 20); sets the timebase to get it."""
        if mdepth is None:
            mdepth = self.get_acquire()["mdepth"] or 100_000
        tb = snap_125(mdepth / (span_hz * SCREEN_DIVISIONS * 2))
        actual = mdepth / (tb * SCREEN_DIVISIONS * 2)
        self.set_timebase_scale(tb)
        return {"timebase_s": tb, "actual_span_hz": actual,
                "freq_resolution_hz": actual / (mdepth / 2)}

    def math_display(self, math_n: int, on: bool):
        self.w(f":MATH{math_n}:DISPlay {'ON' if on else 'OFF'}")

    def get_math(self, math_n: int) -> Dict[str, Any]:
        m = f":MATH{math_n}"
        d = {"display": self.q(f"{m}:DISPlay?"), "operator": self.q(f"{m}:OPERator?"),
             "source1": self.q(f"{m}:SOURce1?"), "source2": self.q(f"{m}:SOURce2?")}
        if d["operator"] == "FFT":
            d.update(fft_center=self.qf(f"{m}:FFT:HCEN?"), fft_window=self.q(f"{m}:FFT:WINDow?"),
                     fft_unit=self.q(f"{m}:FFT:UNIT?"))
        return d

    # ---- cursors / AWG ---------------------------------------------------------------------------------
    def cursor_mode(self, mode: str = "MAN"): self.w(f":CURSor:MODE {mode}")
    def cursor_item(self): return self.q(":CURSor:ITEM?")
    def set_awg_function(self, func: str = "SIN"): self.w(f":SOURce1:FUNCtion {func}")
    def set_awg_frequency(self, hz: float): self.w(f":SOURce1:FREQuency {hz:.6e}")

    def get_awg(self) -> Dict[str, Any]:
        return {"function": self.q(":SOURce1:FUNCtion?"), "frequency": self.qf(":SOURce1:FREQuency?")}

    # ---- Nyquist setup -----------------------------------------------------------------------------------
    @staticmethod
    def plan_nyquist(freq_hz: float, mdepth: int = 100_000) -> Dict[str, Any]:
        """Same arithmetic as scope_setup_for_nyquist() in the notebook."""
        mdepth = min(MEMORY_DEPTHS, key=lambda x: abs(x - mdepth))
        nyq = 1.0 / (2.0 * freq_hz)
        dt = first_125_below(nyq)
        limited = False
        if 1.0 / dt > MAX_SAMPLE_RATE:
            dt = 1.0 / MAX_SAMPLE_RATE
            limited = True
        total = mdepth * dt
        return {"freq_hz": freq_hz, "dt_s": dt, "sample_rate": 1.0 / dt,
                "nyquist_margin": (1.0 / dt) / (2.0 * freq_hz), "total_time_s": total,
                "timebase_s": total / SCREEN_DIVISIONS, "mdepth": mdepth,
                "n_cycles": total * freq_hz, "hardware_limited": limited}

    def setup_for_nyquist(self, freq_hz: float, channel: int = 1, mdepth: int = 100_000,
                          coupling: str = "DC", probe: float = 1, trigger_level_v: float = 0.0,
                          trigger_slope: str = "POS") -> Dict[str, Any]:
        plan = self.plan_nyquist(freq_hz, mdepth)
        self.stop()
        time.sleep(0.1)
        self.w(":TIMebase:MODE MAIN")
        self.w(f":TIMebase:MAIN:SCALe {plan['timebase_s']:.10e}")
        self.w(":TIMebase:MAIN:OFFSet 0")
        self.w(f":CHANnel{channel}:DISPlay ON")
        self.w(f":CHANnel{channel}:COUPling {coupling}")
        self.w(f":CHANnel{channel}:PROBe {probe}")
        self.w(":ACQuire:TYPE NORM")
        self.w(f":ACQuire:MDEPth {plan['mdepth']}")
        self.set_trigger_edge(f"CHAN{channel}", trigger_slope, trigger_level_v, "AUTO")
        self.run()
        plan["channel"] = channel
        return plan

    # ---- 10 MHz reference ------------------------------------------------------------------------
    def set_ext_ref(self, on: bool) -> None:
        """Rear 10 MHz REF IN on/off (Utility → EXT 10M IN)."""
        self.w(f":SYSTem:RCLock {'CINP' if on else 'COUT'}")
        self._ext_ref = bool(on)

    def set_ref_clock(self, mode: str) -> None:
        """CINP (use the external 10 MHz), COUT (output the internal one) or OFF."""
        self.w(f":SYSTem:RCLock {mode}")
        self._ext_ref = str(mode).upper() == "CINP"

    def ext_ref(self) -> Optional[bool]:
        r = self.q(":SYSTem:RCLock?", 2000)
        self._ext_ref = None if r is None else r.strip().upper() == "CINP"
        return self._ext_ref

    def autorange_vertical(self, channel: int = 1, fill_divisions: float = 6.0,
                           passes: int = 4, coarse: bool = True) -> Optional[float]:
        """Adjust V/div so Vpp fills ~6 of 8 divisions (from the monitor notebook).

        ``coarse`` keeps to the 1-2-5 steps (next step up, so the trace always fits)."""
        imp = (self.q(f":CHANnel{channel}:IMPedance?") or "").upper()
        vmax_div = 1.0 if imp.startswith("FIFT") else 10.0
        for _ in range(passes):
            if not self.arm_and_wait():
                break
            vpp = self.measure("vamp", channel)
            cur = self.qf(f":CHANnel{channel}:SCALe?") or 0.2
            if not np.isfinite(vpp) or vpp <= 0:
                self.w(f":CHANnel{channel}:SCALe {min(cur * 2, vmax_div):.6g}")
                continue
            target = min(vpp / fill_divisions, vmax_div)
            if coarse:
                target = min(ceil_125(max(target, VOLTS_PER_DIV[0])), vmax_div)
            if abs(target - cur) / cur < 0.05:
                break
            self.w(f":CHANnel{channel}:SCALe {target:.6g}")
            time.sleep(0.4)
        self.run()
        return self.qf(f":CHANnel{channel}:SCALe?")

    # ---- snapshot / poll ---------------------------------------------------------------------------------
    def autorange_displayed(self, fill_divisions: float = 6.0) -> Dict[int, Optional[float]]:
        """Auto V/div on every displayed channel; returns {channel: V/div}."""
        out = {}
        for n in range(1, 5):
            if (self.q(f":CHANnel{n}:DISPlay?") or "0").strip().upper() in ("1", "ON"):
                out[n] = self.autorange_vertical(n, fill_divisions)
        return out

    def poll(self) -> Dict[str, Any]:
        """Kept to one query: anything more is read when a window asks for it."""
        try:
            st = self.trigger_status()
        except Exception:
            st = None
        return {"trigger_status": st, "ext_ref": self._ext_ref}

    def snapshot(self) -> Dict[str, Any]:
        tb = self.get_timebase()
        acq = self.get_acquire()
        return {"timebase_scale": tb["scale_s"], "timebase_offset": tb["offset_s"],
                "timebase_mode": tb["mode"], "acquire_type": acq["type"],
                "memory_depth": acq["mdepth"], "sample_rate": acq["srate"],
                "channels": self.get_all_channels(), "trigger": self.get_trigger(),
                "ext_ref": self.ext_ref()}
