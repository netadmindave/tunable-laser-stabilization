"""Laser lock sequence: put the tunable laser on the comb with SLICE-OPL #2 (Brimrose AOM).

Steps
  1. comb    — the comb is locked (from the Vescent Comb app's status file)
  2. laser   — wavelength / power set (if given); outside 1549.9–1550.2 nm or 200 µW–1 mW → asks to
               change to 1550.000 nm / 1 mW (always asks; declining keeps the laser as it is); output on
  3. limits  — OPL #2 PLL limits inside the Brimrose driver's 7–12 V window
  4. servo   — OPL #2 servo on, at the OPL target as set (the target is never moved). If the servo is
               already on but the PLL output is railed, the lock is broken first (servo off, then on)
  5. monitor — for the dwell time watch the OPL (servo on, PLL output off the rails, error voltage;
               counter as information only) and, if free, the scope (beat FWHM, peak offset, movement).
               PLL output railed with the servo on → break the lock and relock (up to ``rail_relocks``
               times, each followed by a full clean dwell); still railed → servo left OFF, step fails

The OPL counter is never required to see the beat. The scope is only a monitor: its numbers are
reported, and they fail the lock only if "max FWHM" is set (> 0).

Like the comb sequence: Pause/Stop between actions, every wait has a timeout, dry run writes nothing.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Optional

import numpy as np

from . import scope_owner
from .beat_check import measure_beat_any
from . import laser_setpoints

STEP_IDS = ("comb", "laser", "limits", "beat", "servo", "monitor")
STEP_TITLES = {
    "comb": "Comb is locked (f_rep → GPS, f_ceo)",
    "laser": "Laser on at the set wavelength",
    "limits": "OPL #2 limits inside the Brimrose 7–12 V window",
    "beat": "Beat near the target and steady",
    "servo": "OPL #2 servo ON at the target",
    "monitor": "Watch the lock (OPL + scope)",
}
SCOPE_USER = "Laser lock monitor"


@dataclass
class LaserLockParams:
    wavelength_nm: Optional[float] = None       # None: leave the laser where it is
    power_uw: Optional[float] = None
    require_comb: bool = True
    pll_min_v: float = 7.0
    pll_max_v: float = 12.0
    enforce_limits: bool = True
    rail_margin: float = 0.05                   # PLL output must stay this fraction of the range inside the limits
    rail_relocks: int = 2                       # break + relock this many times when railed, then give up
    break_wait_s: float = 0.5                   # servo off this long when breaking the lock
    setpoint_check: bool = True                 # ask to bring wavelength / power into range (off for relocks)
    window_hz: float = 200.0                    # counter error: shown only, never required
    dwell_s: float = 5.0
    poll_s: float = 0.5
    servo_wait_s: float = 2.0
    scope_channel: int = 2
    beat_role: str = "scope"                    # "scope" (Rigol) or "sa" (HP 8563E): the beat instrument
    scope_span_hz: float = 70e6                 # span the beat instrument watches around the OPL target
    beat_near_hz: float = 10e6                  # before the servo: beat within this of the target …
    beat_still_hz: float = 10e6                 # … moving less than this (peak to peak) …
    beat_still_s: float = 30.0                  # … for this long
    beat_timeout_s: float = 600.0
    beat_every_s: float = 1.0
    scope_every_s: float = 1.0
    max_fwhm_hz: float = 0.0                    # 0 = report only
    dry_run: bool = False

    def as_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        p = cls()
        for k, v in (d or {}).items():
            if hasattr(p, k):
                setattr(p, k, v)
        return p


@dataclass
class StepState:
    id: str
    title: str
    status: str = "wait"
    detail: str = ""


class Aborted(Exception):
    pass


class LaserLockSequence:
    """``devices``: laser, opl2 (required), scope (optional: monitor only).
    ``comb_status() -> (ok, note)`` reports the comb lock (default: the Vescent Comb app's status file)."""

    def __init__(self, devices: Dict[str, Any], params: Optional[LaserLockParams] = None,
                 on_step=None, on_log=None, on_sample=None,
                 ask=None, comb_status: Optional[Callable[[], Any]] = None):
        self.d = devices
        if comb_status is None:
            from .comb_link import comb_locked
            comb_status = comb_locked
        self.comb_status = comb_status
        self.p = params or LaserLockParams()
        self.on_step = on_step or (lambda s: None)
        self.on_log = on_log or (lambda m: None)
        self.on_sample = on_sample or (lambda s: None)
        self.ask = ask or (lambda q, rows=None: True)
        self.steps = {sid: StepState(sid, STEP_TITLES[sid]) for sid in STEP_IDS}
        self._stop = threading.Event()
        self._pause = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.result: Optional[bool] = None

    # ---- control ------------------------------------------------------------------------------------
    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        return self.thread

    def stop(self):
        self._stop.set()

    def pause(self, on: bool = True):
        (self._pause.set if on else self._pause.clear)()

    def _checkpoint(self):
        while self._pause.is_set() and not self._stop.is_set():
            time.sleep(0.1)
        if self._stop.is_set():
            raise Aborted()

    def _sleep(self, s):
        end = time.time() + s
        while time.time() < end:
            self._checkpoint()
            time.sleep(min(0.1, max(0.0, end - time.time())))

    def _set(self, sid, status, detail=""):
        st = self.steps[sid]
        st.status, st.detail = status, detail
        self.on_step(st)

    def _log(self, m):
        self.on_log(m)

    def run(self) -> bool:
        try:
            self.result = self._run()
        except Aborted:
            for st in self.steps.values():
                if st.status == "run":
                    self._set(st.id, "fail", "stopped")
            self._log("laser lock stopped")
            self.result = False
        except Exception as e:
            for st in self.steps.values():
                if st.status == "run":
                    self._set(st.id, "fail", f"error: {e}")
            self._log(f"laser lock error: {e}")
            self.result = False
        return bool(self.result)

    # ---- steps ---------------------------------------------------------------------------------------
    def _run(self) -> bool:
        p, dry = self.p, self.p.dry_run
        laser, opl2 = self.d.get("laser"), self.d.get("opl2")
        if laser is None or opl2 is None:
            missing = [r for r, d in (("tunable laser", laser), ("OPL #2", opl2)) if d is None]
            self._set("comb", "fail", "not connected: " + ", ".join(missing))
            return False

        # 1. comb ---------------------------------------------------------------------------------
        self._checkpoint()
        self._set("comb", "run")
        ok, note = self.comb_status()
        if not ok and p.require_comb:
            self._set("comb", "fail", note + " → lock the comb in the Vescent Comb app first")
            return False
        self._set("comb", "done" if ok else "skip", note)

        # 2. laser ---------------------------------------------------------------------------------
        self._checkpoint()
        self._set("laser", "run")
        if dry:
            self._set("laser", "skip", "dry run: would set "
                      + (f"{p.wavelength_nm:.3f} nm " if p.wavelength_nm else "")
                      + (f"{p.power_uw:g} µW " if p.power_uw else "") + "and turn the output on")
        else:
            if p.wavelength_nm:
                laser.set_wavelength_nm(p.wavelength_nm)
            if p.power_uw and hasattr(laser, "set_power_uw"):
                laser.set_power_uw(p.power_uw)
            snap = laser.poll()
            ch = laser_setpoints.check(snap.get("wavelength_nm"), snap.get("power_w")) if p.setpoint_check else {}
            if ch:
                q = laser_setpoints.describe(ch)
                if self.ask(q + "\n\nChange it?", {"always": True}):
                    laser_setpoints.apply(laser, ch)
                    self._log("laser: " + q.replace("\n", "; "))
                    time.sleep(0.3)
                    snap = laser.poll()
                else:
                    self._log("laser: left out of range as asked (" + q.replace("\n", "; ") + ")")
            if not snap.get("output_on"):
                if not self.ask("Turn the tunable laser output ON?", None):
                    self._set("laser", "fail", "output left off (declined)")
                    return False
                laser.output_on(confirm=True)
                time.sleep(0.3)
                snap = laser.poll()
            if not snap.get("output_on"):
                self._set("laser", "fail", "output did not report ON")
                return False
            wl, pw = snap.get("wavelength_nm"), snap.get("power_w")
            self._set("laser", "done", "output ON" + (f" · {wl:.3f} nm" if isinstance(wl, float) else "")
                      + (f" · {pw * 1e6:.0f} µW" if isinstance(pw, float) else ""))
            self._log(f"laser: {self.steps['laser'].detail}")

        # 3. limits -------------------------------------------------------------------------------
        self._checkpoint()
        self._set("limits", "run")
        lo, hi = opl2.get_pll_min(), opl2.get_pll_max()
        inside = isinstance(lo, float) and isinstance(hi, float) and p.pll_min_v <= lo < hi <= p.pll_max_v
        if inside:
            self._set("limits", "done", f"PLLMIN {lo:.1f} V · PLLMAX {hi:.1f} V")
        elif dry or not p.enforce_limits:
            self._set("limits", "skip" if dry else "fail", f"PLLMIN {lo} · PLLMAX {hi} outside "
                      f"{p.pll_min_v:g}–{p.pll_max_v:g} V" + (" (dry run)" if dry else ""))
            if not dry:
                return False
        else:
            bias = opl2.get_pll_bias()
            bias = min(max(bias if isinstance(bias, float) else (p.pll_min_v + p.pll_max_v) / 2, p.pll_min_v), p.pll_max_v)
            opl2.set_pll_limits(p.pll_min_v, p.pll_max_v, bias)
            self._set("limits", "done", f"set PLLMIN {p.pll_min_v:g} V · PLLMAX {p.pll_max_v:g} V · bias {bias:.2f} V")

        # 3b. beat near the target and steady (free-running), before the servo goes on --------------
        if not dry and not self._beat_gate(opl2):
            return False

        # 4. servo ---------------------------------------------------------------------------------
        self._checkpoint()
        self._set("servo", "run")
        tgt = opl2.get_target_beatnote()
        tgt_txt = f"target {tgt:.6f} MHz" if isinstance(tgt, float) else "target ?"
        if dry:
            self._set("servo", "skip", f"dry run · {tgt_txt}")
            self._set("monitor", "skip", "dry run")
            return True
        note = ""
        if opl2.servo_on():
            if self.pll_railed(opl2.read_voltage("pll_out"), opl2.get_pll_min(), opl2.get_pll_max()):
                self._log("OPL #2 servo on but the PLL output is railed — breaking the lock")
                self._break(opl2)
                note = " · was railed: lock broken and restarted"
            else:
                note = " · was already on"
        opl2.set_servo(True)
        self._sleep(p.servo_wait_s)
        if not opl2.servo_on():
            self._set("servo", "fail", "servo did not report ON")
            return False
        self._set("servo", "done", f"SERVO ON · {tgt_txt}{note}")
        self._log(f"OPL #2 SERVO ON · {tgt_txt}{note}")

        # 5. monitor -------------------------------------------------------------------------------
        return self._monitor(opl2, tgt * 1e6 if isinstance(tgt, float) else None)

    def _break(self, opl2):
        """Break the lock: servo off for ``break_wait_s`` (lets the integrator let go of the rail)."""
        opl2.set_servo(False)
        self._sleep(self.p.break_wait_s)

    def pll_railed(self, out, lo, hi) -> Optional[bool]:
        """True if the PLL output sits within ``rail_margin`` of PLLMIN/PLLMAX (None if unreadable)."""
        if not all(isinstance(x, float) for x in (out, lo, hi)) or hi <= lo:
            return None
        m = self.p.rail_margin * (hi - lo)
        return not (lo + m < out < hi - m)

    def _beat_gate(self, opl2) -> bool:
        """Wait until the beat is within beat_near_hz of the OPL target and has moved less than beat_still_hz
        (peak to peak) for beat_still_s, watched with the chosen beat instrument. Skipped if already locked."""
        p = self.p
        self._checkpoint()
        self._set("beat", "run", "watching the beat")
        if opl2.servo_on():
            if not self.pll_railed(opl2.read_voltage("pll_out"), opl2.get_pll_min(), opl2.get_pll_max()):
                self._set("beat", "skip", "already locked (servo on, PLL output off its rails)")
                return True
            self._log("OPL #2 servo on but the PLL output is railed — breaking the lock before checking the beat")
            self._break(opl2)
        tgt = opl2.get_target_beatnote()
        dev = self.d.get(p.beat_role)
        name = "spectrum analyzer" if p.beat_role == "sa" else "scope"
        if dev is None or not isinstance(tgt, float):
            self._set("beat", "skip", f"no {name} connected: beat position not checked" if dev is None
                      else "OPL target unreadable: beat position not checked")
            return True
        target = tgt * 1e6
        if not scope_owner.acquire(SCOPE_USER, wait_s=5.0):
            self._set("beat", "skip", scope_owner.blocked_reason(SCOPE_USER) or f"{name} busy")
            return True
        hist = []                     # (time, peak) since the beat last became near and steady
        t0 = time.time()
        try:
            while True:
                self._checkpoint()
                now = time.time()
                try:
                    r = measure_beat_any(dev, target, p.scope_span_hz, p.scope_channel, trace=True)
                except Exception as e:
                    r = {}
                    self._set("beat", "run", f"{name} capture failed: {e}")
                pk = r.get("peak_hz", float("nan"))
                if math.isfinite(pk) and abs(pk - target) <= p.beat_near_hz:
                    hist.append((now, pk))                       # the current steady stretch
                    while len(hist) > 1 and max(h[1] for h in hist) - min(h[1] for h in hist) >= p.beat_still_hz:
                        hist.pop(0)                              # moved too much: the stretch starts later
                    pp = max(h[1] for h in hist) - min(h[1] for h in hist)
                    held = now - hist[0][0]
                    off = pk - target
                    self._set("beat", "run", f"offset {'+' if off >= 0 else '−'}{_hz(abs(off))} · moved {_hz(pp)} "
                                             f"over {held:.0f} / {p.beat_still_s:g} s")
                    self.on_sample({"t": now, "err_hz": None, "fwhm_hz": r.get("fwhm_hz"), "peak_off_hz": off,
                                    "peak_hz": pk, "target_hz": target, "level_dbv": r.get("level_dbv"),
                                    "level_dbm": r.get("level_dbm"), "rbw_hz": r.get("rbw_hz"),
                                    "f": r.get("f"), "p_db": r.get("p_db")})
                    if held >= p.beat_still_s and len(hist) >= 2:
                        self._set("beat", "done", f"within {_hz(abs(off))} of the target, moved {_hz(pp)} in "
                                                  f"{held:.0f} s")
                        return True
                else:
                    hist.clear()
                    self._set("beat", "run", ("no beat" if not math.isfinite(pk) else
                                              f"beat {_hz(abs(pk - target))} from the target (needs ≤ "
                                              f"{_hz(p.beat_near_hz)})") + f" · {now - t0:.0f} s")
                if now - t0 > p.beat_timeout_s:
                    self._set("beat", "fail", f"beat not within {_hz(p.beat_near_hz)} and steady for "
                                              f"{p.beat_still_s:g} s after {p.beat_timeout_s:g} s")
                    return False
                self._sleep(p.beat_every_s)
        finally:
            scope_owner.release(SCOPE_USER)

    def _monitor(self, opl2, target_hz: Optional[float]) -> bool:
        p = self.p
        self._set("monitor", "run", "watching the OPL")
        scope = self.d.get(p.beat_role)
        name = "spectrum analyzer" if p.beat_role == "sa" else "scope"
        scope_note = ""
        have_scope = False
        if scope is None:
            scope_note = f"no {name} connected"
        elif target_hz is None:
            scope_note = "scope: OPL target unreadable"
        elif scope_owner.acquire(SCOPE_USER, wait_s=5.0):
            have_scope = True
        else:
            scope_note = scope_owner.blocked_reason(SCOPE_USER) or "scope busy"
        try:
            lo, hi = opl2.get_pll_min(), opl2.get_pll_max()
            t_end = time.time() + p.dwell_s
            last_scope = 0.0
            peaks, fwhms, railed_n, out = [], [], 0, None
            relocks = 0
            while time.time() < t_end:
                self._checkpoint()
                if not opl2.servo_on():
                    self._set("monitor", "fail", "OPL #2 servo dropped")
                    return False
                out = opl2.read_voltage("pll_out")
                err_v = opl2.read_voltage("error")
                railed = self.pll_railed(out, lo, hi)
                railed_n = railed_n + 1 if railed else 0
                if railed_n >= 2:                       # two samples in a row on the rail: not locked
                    rail_txt = f"PLL output {out:.2f} V on the rail (limits {lo:.1f}–{hi:.1f} V)"
                    if relocks >= p.rail_relocks:
                        opl2.set_servo(False)
                        self._set("monitor", "fail", f"{rail_txt} after {relocks} relock(s) — servo left OFF")
                        self._log(f"OPL #2 still railed after {relocks} relock(s); servo OFF")
                        return False
                    relocks += 1
                    self._set("monitor", "run", f"{rail_txt} — breaking the lock, relock {relocks}/{p.rail_relocks}")
                    self._log(f"OPL #2 railed with the servo on — breaking the lock and relocking "
                              f"({relocks}/{p.rail_relocks})")
                    self._break(opl2)
                    opl2.set_servo(True)
                    self._sleep(p.servo_wait_s)
                    railed_n, peaks, fwhms = 0, [], []
                    t_end = time.time() + p.dwell_s       # a full clean dwell after every relock
                    continue
                b = opl2.read_beatnote()                # information only
                err_hz = ((target_hz / 1e6 - b) * 1e6 if target_hz is not None and isinstance(b, float) and b > 1
                          else None)
                s = {"t": time.time(), "err_hz": err_hz, "pll_out_v": out, "err_v": err_v,
                     "fwhm_hz": None, "peak_off_hz": None}
                if have_scope and time.time() - last_scope >= p.scope_every_s:
                    last_scope = time.time()
                    try:
                        r = measure_beat_any(scope, target_hz, p.scope_span_hz, p.scope_channel, trace=True)
                    except Exception as e:
                        r = {}
                        scope_note = f"{name} capture failed: {e}"
                    if math.isfinite(r.get("fwhm_hz", float("nan"))):
                        peaks.append(r["peak_hz"])
                        fwhms.append(r["fwhm_hz"])
                        s.update(fwhm_hz=r["fwhm_hz"], peak_off_hz=r["peak_hz"] - target_hz,
                                 peak_hz=r["peak_hz"], target_hz=target_hz,
                                 level_dbv=r["level_dbv"], level_dbm=r.get("level_dbm"), rbw_hz=r["rbw_hz"],
                                 f=r.get("f"), p_db=r.get("p_db"))
                    elif r:
                        scope_note = (f"{name}: no beat in the span" +
                                      (" (check timebase / sample rate)" if p.beat_role == "scope" else ""))
                self.on_sample(s)
                self._sleep(p.poll_s)
        finally:
            if have_scope:
                scope_owner.release(SCOPE_USER)

        parts = [f"servo held {p.dwell_s:g} s" + (f" (after {relocks} relock(s))" if relocks else ""), f"PLL out {out:.2f} V" if isinstance(out, float) else "PLL out ?"]
        if fwhms:
            fw = float(np.median(fwhms))
            move = float(np.std(peaks)) if len(peaks) > 1 else 0.0
            off = float(np.mean(peaks)) - target_hz
            parts.append(f"{name} FWHM {_hz(fw)} · offset {'+' if off >= 0 else '−'}{_hz(abs(off))} · move {_hz(move)}")
            if p.max_fwhm_hz > 0 and fw > p.max_fwhm_hz:
                self._set("monitor", "fail", " · ".join(parts) + f" — FWHM above {_hz(p.max_fwhm_hz)}")
                return False
        elif scope_note:
            parts.append(scope_note)
        self._set("monitor", "done", " · ".join(parts))
        self._log("laser locked to the comb · " + " · ".join(parts[2:] or parts))
        return True


def _hz(x: float) -> str:
    for scale, unit in ((1e6, "MHz"), (1e3, "kHz")):
        if abs(x) >= scale:
            return f"{x / scale:.3g} {unit}"
    return f"{x:.3g} Hz"
