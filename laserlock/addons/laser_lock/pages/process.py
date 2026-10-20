"""Laser lock — one page with everything the laser→comb lock needs: laser, OPL #2, comb state,
the scope beat monitor (same panel as on the OPL #2 page), the lock steps and the trends.

"Locked" means OPL #2 servo on with the PLL output off its rails; the OPL counter is information only.
The scope is only a monitor (beat FWHM / offset / movement); there is no separate scope window."""
from __future__ import annotations

import threading
import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QMessageBox, QVBoxLayout

from laserlock.addonkit import REGISTRY
from laserlock.core.units import C_LIGHT, dbm_to_w, eng, nm_to_thz, snap_to_grid, w_to_dbm
from ..comb_tooth import laser_sigma_hz, nearest_tooth
from laserlock.gui import theme as T
from laserlock.gui import widgets as W
from laserlock.gui.page_base import Page

from .. import laser_setpoints, scope_owner
from ..comb_link import comb_locked
from ..laser_sequence import STEP_IDS, STEP_TITLES, LaserLockParams, LaserLockSequence
from . import beat_monitor
from .beat_monitor import BeatMonitor
from .opl2 import run_beat_check


def pll_railed(d, margin=0.05):
    """True / False from an OPL poll dict (None if the voltages aren't there)."""
    lo, hi, out = d.get("pll_min"), d.get("pll_max"), d.get("pll_out_v")
    if not all(isinstance(x, float) for x in (lo, hi, out)) or hi <= lo:
        return None
    m = margin * (hi - lo)
    return not (lo + m < out < hi - m)


class _Bridge(QObject):
    step = Signal(object)
    log = Signal(str)
    sample = Signal(dict)
    finished = Signal(bool)
    ask = Signal(str, object)
    beat = Signal(object)
    spectrum = Signal(object)
    owner = Signal()


class LaserLockPage(Page):
    TITLE = "Laser lock"
    ROLE = None

    def __init__(self, hub, settings, main=None):
        super().__init__(hub, settings, main)
        k = "ui.laserlock"
        self.pill_comb = W.Pill("comb —")
        self.pill_laser = W.Pill("laser —")
        self.pill_opl = W.Pill("OPL #2 —")
        self.header("Laser lock", "Tunable laser → comb through SLICE-OPL #2 and the Brimrose AOM.",
                    [self.pill_comb, self.pill_laser, self.pill_opl],
                    [W.button("Laser page", slot=lambda: main and main.show_page("laser")),
                     W.button("OPL #2 page", slot=lambda: main and main.show_page("opl2"))])
        self.br = _Bridge()
        self.br.step.connect(self._on_step)
        self.br.log.connect(lambda m: (self.hub.emit_log("LASERLOCK", m), self.l_log.setText(m)))
        self.br.sample.connect(self._on_sample)
        self.br.finished.connect(self._finished)
        self.br.ask.connect(self._ask_gui)
        self.br.beat.connect(self._beat_result)
        self._ask_evt, self._ask_ans = threading.Event(), False
        self.seq = None

        g = QGridLayout()
        g.setSpacing(14)
        self.v.addLayout(g)

        # laser -------------------------------------------------------------------------------------
        p = W.Panel("Tunable laser")
        self.r_wl = W.Readout("Wavelength", big=True)
        self.r_nu = W.Readout("Frequency")
        self.r_pw = W.Readout("Power")
        self.r_out = W.Readout("Output")
        p.add(W.hbox(self.r_wl, None))
        p.add(W.hbox(self.r_nu, self.r_pw, self.r_out, None))
        self.e_wl = W.dspin(1550.0, 1400, 1700, 3, 0.01, "nm")               # filled from the laser
        self.e_wl.editingFinished.connect(self._snap_wl)
        self.e_dbm = W.dspin(0.0, -60, 13, 2, 0.1, "dBm")                    # filled from the laser
        self.e_w = W.EngEdit(dbm_to_w(0.0), "W")
        self.e_dbm.editingFinished.connect(lambda: self._p_edited("dbm"))
        self.e_w.editingFinished.connect(lambda: self._p_edited("w"))
        p.add(W.hbox(W.field("Wavelength", self.e_wl), W.button("Set", slot=self.set_wl), None))
        p.add(W.hbox(W.field("Power", self.e_dbm), W.field("=", self.e_w), W.button("Set", slot=self.set_pw), None))
        p.add(W.hbox(W.button("Output ON", "ok", self.laser_on), W.button("Output OFF", "danger", self.laser_off), None))
        self.pull = laser_setpoints.FieldPull(self.e_wl, self.e_dbm, self.e_w)
        self._sp_asked = False                  # range question asked for this laser connection
        g.addWidget(p, 0, 0)

        # OPL #2 ---------------------------------------------------------------------------------------
        p = W.Panel("SLICE-OPL #2 · Brimrose AOM")
        self.r_bn = W.Readout("Counter", big=True)
        self.r_tgt = W.Readout("Target")
        self.r_err = W.Readout("Error")
        self.r_pll = W.Readout("PLL out")
        p.add(W.hbox(self.r_bn, None))
        p.add(W.hbox(self.r_tgt, self.r_err, self.r_pll, None))
        self.e_tgt = W.EngEdit(50e6, "Hz")
        self.seg_servo = W.Seg(["Servo off", "Servo on"])
        self.seg_servo.changed.connect(self.set_servo)
        p.add(W.hbox(W.field("Target", self.e_tgt), W.button("Set", slot=self.set_target), self.seg_servo, None))
        self.b_check = W.button("Beat check", slot=self.beat_check)
        self.b_check.setToolTip("Counter first, then the scope; only looks, never moves the target")
        self.l_check = W.label("", "mono")
        self.l_check.setWordWrap(True)
        p.add(W.hbox(self.b_check, None))
        p.add(self.l_check)
        g.addWidget(p, 0, 1)

        # comb ----------------------------------------------------------------------------------------
        p = W.Panel("Comb (from the Vescent Comb app)")
        self.r_frep = W.Readout("f_rep → GPS · OPL #1")
        self.r_ceo = W.Readout("f_ceo · FPGA")
        self.r_ffc = W.Readout("FFC-100")
        self.r_tooth = W.Readout("Laser beats against tooth")
        p.add(W.grid([self.r_frep, self.r_ceo, self.r_ffc, self.r_tooth], 1))
        self.l_comb = W.label("", "lbl", wrap=True)
        p.add(self.l_comb)
        g.addWidget(p, 0, 2)

        # steps ------------------------------------------------------------------------------------------
        self.pill_seq = W.Pill("idle")
        p = W.Panel("Lock steps", self.pill_seq)
        self.rows = {}
        for i, sid in enumerate(STEP_IDS):
            r = W.StepRow(i + 1, STEP_TITLES[sid])
            self.rows[sid] = r
            p.add(r)
        self.ck_wl = W.bind(settings, f"{k}.set_wl", QCheckBox("Set the wavelength above first"), False)
        self.ck_comb = W.bind(settings, f"{k}.require_comb", QCheckBox("Require the comb locked"), True)
        self.ck_lim = W.bind(settings, f"{k}.enforce_limits", QCheckBox("Set OPL #2 limits to 7–12 V if outside"), True)
        self.ck_dry = W.bind(settings, f"{k}.dry_run", QCheckBox("Dry run (read only)"), False)
        self.e_win = W.bind(settings, f"{k}.window_hz", W.dspin(200, 1, 1e6, 0, 10, "Hz"), 200)
        self.e_win.setToolTip("Counter error band shown on the trend (information only, never required)")
        self.e_dwell = W.bind(settings, f"{k}.dwell_s", W.dspin(5, 0.5, 600, 1, 1, "s"), 5)
        self.e_fmax = W.bind(settings, f"{k}.max_fwhm_hz", W.EngEdit(0.0, "Hz"), 0.0)
        self.e_fmax.setToolTip("0 Hz = report only")
        p.add(W.grid([self.ck_wl, self.ck_comb, self.ck_lim, self.ck_dry], 2))
        p.add(W.hbox(W.field("Watch for", self.e_dwell), W.field("Counter band (info)", self.e_win), None))
        p.add(W.hbox(W.field("Max FWHM (0 = report only)", self.e_fmax), None))
        # before the servo goes on: the free-running beat must be near the target and steady
        self.e_near = W.bind(settings, f"{k}.beat_near_hz", W.EngEdit(10e6, "Hz"), 10e6)
        self.e_still = W.bind(settings, f"{k}.beat_still_hz", W.EngEdit(10e6, "Hz"), 10e6)
        self.e_still_s = W.bind(settings, f"{k}.beat_still_s", W.dspin(30, 0, 3600, 0, 5, "s"), 30)
        self.e_btmo = W.bind(settings, f"{k}.beat_timeout_s", W.dspin(600, 10, 7200, 0, 30, "s"), 600)
        self.e_near.setToolTip("The beat must be within this of the OPL target before the servo goes on")
        self.e_still.setToolTip("… and must move less than this (peak to peak) …")
        self.e_still_s.setToolTip("… for this long. 0 s = only check that it's near.")
        self.e_btmo.setToolTip("Give up (servo stays off) if that isn't reached in this time")
        p.add(W.label("Beat check before the servo (uses the beat instrument and its span):", "lbl"))
        p.add(W.grid([W.field("Within", self.e_near), W.field("Moving less than", self.e_still),
                      W.field("For", self.e_still_s), W.field("Give up after", self.e_btmo)], 4))
        p.add(W.label("Servo on at the OPL target as set; passes while the servo stays on and the PLL output stays "
                      "off its rails. The scope (beat monitor channel) only watches: FWHM, offset and movement.", "hint",
                      wrap=True))
        self.b_start = W.button("Lock laser", "primary", self.start)
        self.b_stop = W.button("Stop", "danger", self.stop)
        self.b_stop.setEnabled(False)
        p.add(W.hbox(self.b_start, self.b_stop, None))
        self.l_log = W.label("", "mono")
        self.l_log.setWordWrap(True)
        p.add(self.l_log)
        g.addWidget(p, 1, 0, 2, 1)

        # relock watchdog ---------------------------------------------------------------------------------
        self.pill_wd = W.Pill("off")
        p = W.Panel("Relock watchdog", self.pill_wd)
        self.ck_wd = W.bind(settings, f"{k}.watchdog.on", QCheckBox("Relock automatically if the laser lock drops"),
                            False)
        self.ck_wd.toggled.connect(lambda on: self._wd_state("armed" if on else "off"))
        self.e_wd_wait = W.bind(settings, f"{k}.watchdog.wait_s", W.EngEdit(10.0, "s"), 10.0)
        self.e_wd_max = W.bind(settings, f"{k}.watchdog.max_per_hour", W.ispin(3, 1, 60), 3)
        self.e_wd_err = W.bind(settings, f"{k}.watchdog.err_hz", W.EngEdit(10e3, "Hz"), 10e3)
        self.ck_rail = W.bind(settings, f"{k}.watchdog.rail_relock",
                              QCheckBox("Break and relock when the PLL output rails with the servo on"), True)
        self.e_rail_wait = W.bind(settings, f"{k}.watchdog.rail_wait_s", W.EngEdit(2.0, "s"), 2.0)
        p.add(self.ck_wd)
        p.add(W.grid([W.field("Lost for longer than", self.e_wd_wait), W.field("Error above", self.e_wd_err),
                      W.field("At most per hour", self.e_wd_max)], 3))
        p.add(W.hbox(self.ck_rail, W.field("Railed for longer than", self.e_rail_wait), None))
        self.l_wd = W.label("Arms itself once the laser is locked; turning the OPL #2 servo off by hand disarms it "
                            "until the next lock.", "hint")
        p.add(self.l_wd)
        g.addWidget(p, 3, 0)

        self._wd = {"locked_once": False, "lost_since": None, "relocks": [], "user_off": False, "running": False,
                    "rail_since": None}

        # scope beat monitor (same panel as on the OPL #2 page) ---------------------------------------------
        self.mon = BeatMonitor(hub, settings)
        g.addWidget(self.mon, 1, 1, 1, 2)

        p = W.Panel("OPL #2 beat error")
        self.trend = W.plot(180, "Error (Hz)", "minutes", title="laser_beat_error")
        self.c_trend = self.trend.plot(pen=W.pen(T.PLOT1))
        self.win = pg.LinearRegionItem(values=(-200, 200), orientation="horizontal", movable=False,
                                       brush=pg.mkBrush(24, 57, 46, 120), pen=pg.mkPen(T.OK))
        self.trend.addItem(self.win, ignoreBounds=True)
        self.hist = W.History()
        p.add(self.trend)
        self.strend = W.plot(160, "Hz", "minutes", title="laser_beat_scope")
        self.strend.addLegend(offset=(10, 10))
        self.c_fwhm = self.strend.plot(pen=W.pen(T.PLOT2), name="scope FWHM")
        self.c_poff = self.strend.plot(pen=W.pen(T.PLOT3), name="peak − target")
        self.shist = W.History()
        p.add(self.strend)
        g.addWidget(p, 2, 1, 2, 2)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(2, 1)
        self.v.addStretch(1)

        self.comb_timer = QTimer(self)
        self.comb_timer.timeout.connect(self._comb_pill)
        self.comb_timer.start(2000)
        self._comb_pill()

    # ---- data -------------------------------------------------------------------------------------------
    def on_devices_changed(self):
        if not self.hub.has("laser"):
            self._sp_asked = False               # ask again after the next connect
        for role, pill in (("laser", self.pill_laser), ("opl2", self.pill_opl)):
            if not self.hub.has(role):
                pill.set(f"{'laser' if role == 'laser' else 'OPL #2'} not connected", "idle")

    def on_poll(self, role, d):
        if role == "laser":
            wl = d.get("wavelength_nm")
            self.r_wl.set(f"{wl:.3f} nm" if isinstance(wl, float) else None)
            self.r_nu.set(eng(nm_to_thz(wl) * 1e12, "Hz", 8) if isinstance(wl, float) else None)
            pw = d.get("power_w")
            self.r_pw.set(f"{eng(pw, 'W', 4)} · {w_to_dbm(pw):.2f} dBm" if isinstance(pw, float) and pw > 0 else None)
            if self.pull.free():                 # entry fields follow the laser unless you are editing them
                if isinstance(wl, float) and wl > 0:
                    self.e_wl.blockSignals(True)
                    self.e_wl.setValue(wl)
                    self.e_wl.blockSignals(False)
                if isinstance(pw, float) and pw > 0:
                    self.e_dbm.blockSignals(True)
                    self.e_dbm.setValue(round(w_to_dbm(pw), 2))
                    self.e_dbm.blockSignals(False)
                    self.e_w.setValue(pw)
            if not self._sp_asked and isinstance(wl, float) and isinstance(pw, float):
                self._sp_asked = True
                ch = laser_setpoints.check(wl, pw)
                busy = self.seq is not None and self.b_stop.isEnabled()
                if ch and not busy:
                    QTimer.singleShot(0, lambda ch=ch: self._ask_setpoints(ch))
            self._tooth()
            on = d.get("output_on")
            self.r_out.set("ON" if on else "off", "{}", T.WARN if on else None)
            self.pill_laser.set("laser output ON" if on else "laser output off", "warn" if on else "idle")
        elif role == "opl2":
            b, t = d.get("beatnote"), d.get("target_beatnote")
            has = isinstance(b, float) and b > 1
            servo = d.get("servo_on")
            self.r_bn.set(eng(b * 1e6, "Hz", 9) if has else "no beat", "{}", None if has else T.WARN)
            self.r_tgt.set(eng(t * 1e6, "Hz", 7) if isinstance(t, float) else None)
            err = (t - b) * 1e6 if has and isinstance(t, float) else None
            win = self.e_win.value()
            self.r_err.set(("+" if err >= 0 else "−") + eng(abs(err), "Hz", 4) if err is not None else None, "{}",
                           T.OK if err is not None and abs(err) <= win else T.WARN)
            self.r_pll.set(eng(d["pll_out_v"], "V", 4) if isinstance(d.get("pll_out_v"), float) else None)
            self.seg_servo.blockSignals(True)
            self.seg_servo.set_index(1 if servo else 0)
            self.seg_servo.blockSignals(False)
            if isinstance(t, float):
                if not self.e_tgt.hasFocus():
                    self.e_tgt.setValue(t * 1e6)
            railed = pll_railed(d)
            locked = bool(servo) and railed is False
            self.pill_opl.set("laser locked" if locked else ("servo on · PLL on the rail" if servo else
                              "servo off"), "ok" if locked else ("warn" if servo else "idle"))
            self.hist.add(err=err)
            tt, y = self.hist.series("err")
            self.c_trend.setData(tt, y)
            self.win.setRegion((-win, win))
            self._tooth()
            if not self._rail_guard(bool(servo), railed, d):
                self._watchdog(locked, err)

    def _ask_setpoints(self, ch):
        """Laser read for the first time since connecting and out of range: ask (always) to change it."""
        q = laser_setpoints.describe(ch)
        if _ask_always(self, "Tunable laser", q + "\n\nChange it?", "Change"):
            self.call(lambda d: laser_setpoints.apply(d, ch), log="laser: " + q.replace("\n", "; "), role="laser")
        else:
            self.hub.emit_log("LASER", "left as it is: " + q.replace("\n", "; "))

    def _tooth(self):
        wl = self.hub.last("laser").get("wavelength_nm")
        if not isinstance(wl, float) or wl <= 0:
            self.r_tooth.set(None)
            return
        s = self.settings
        frep = float(s.get("ui.laser.comb.frep_hz", 100e6) or 100e6)
        from ..comb_link import fceo_hz
        ref = fceo_hz(s) if s.get("ui.laser.comb.ceo_src", "fpga") == "fpga" else None
        fceo = ref if ref else float(s.get("ui.laser.comb.fceo_hz", 20e6) or 0)
        fceo *= int(s.get("ui.laser.comb.sign", 1) or 1)
        known = float(s.get("ui.laser.comb.known_hz", 0) or 0)
        nu = known if known > 0 else C_LIGHT / (wl * 1e-9)
        model = s.get("ui.laser.model", "hp8168e")
        acc = {"hp8168d": 0.2}.get(model, 0.1)
        b = self.hub.last("opl2").get("beatnote")
        tt = nearest_tooth(nu, frep, fceo, None if known > 0 else laser_sigma_hz(nu, acc),
                           b * 1e6 if isinstance(b, float) and b > 1 else None)
        self.r_tooth.set(f"n = {tt.n:,}" + (f" ± {tt.n_uncertainty}" if tt.n_uncertainty else "")
                         + f" · {eng(tt.nu_n_hz, 'Hz', 11)}")

    # ---- relock watchdog -------------------------------------------------------------------------------
    def _wd_state(self, text, state=None):
        st = state or {"off": "idle", "armed": "ok", "watching": "ok", "relocking": "warn", "lost": "warn",
                       "stopped": "bad"}.get(text.split(" ")[0], "idle")
        self.pill_wd.set(text, st)

    def _watchdog(self, locked, err):
        """``locked``: servo on and PLL output off the rails. The counter error counts only when it reads."""
        wd = self._wd
        if not self.ck_wd.isChecked() or wd["running"] or (self.seq is not None and self.b_stop.isEnabled()):
            return
        locked = locked and (err is None or abs(err) <= self.e_wd_err.value())
        if locked:
            wd["locked_once"], wd["lost_since"], wd["user_off"] = True, None, False
            self._wd_state("watching")
            return
        if not wd["locked_once"] or wd["user_off"]:
            self._wd_state("armed" if not wd["user_off"] else "armed · servo off by hand")
            return
        now = time.time()
        if wd["lost_since"] is None:
            wd["lost_since"] = now
        lost_for = now - wd["lost_since"]
        self._wd_state(f"lost {lost_for:.0f} s")
        if lost_for < self.e_wd_wait.value():
            return
        wd["relocks"] = [x for x in wd["relocks"] if now - x < 3600]
        if len(wd["relocks"]) >= self.e_wd_max.value():
            self.ck_wd.setChecked(False)
            self._wd_state("stopped · hourly limit reached")
            self.hub.emit_log("WATCHDOG", f"laser lock lost again; {len(wd['relocks'])} relocks in the last hour — "
                                          "watchdog switched off")
            return
        wd["relocks"].append(now)
        wd["lost_since"] = None
        wd["running"] = True
        self._wd_state(f"relocking ({len(wd['relocks'])}/{self.e_wd_max.value()} this hour)")
        self.hub.emit_log("WATCHDOG", f"laser lock lost for {lost_for:.0f} s — relocking "
                                      f"({len(wd['relocks'])} in the last hour)")
        self.start(from_watchdog=True)

    def _rail_guard(self, servo, railed, d) -> bool:
        """Servo on + PLL output railed for longer than the set time → break the lock and relock (the
        sequence's servo step switches the servo off first). Shares the watchdog's per-hour limit.
        Returns True when it started a relock."""
        wd = self._wd
        if not (servo and railed) or not self.ck_rail.isChecked():
            wd["rail_since"] = None
            return False
        if wd["running"] or (self.seq is not None and self.b_stop.isEnabled()):
            return False                                   # the sequence handles rails itself
        now = time.time()
        if wd["rail_since"] is None:
            wd["rail_since"] = now
        if now - wd["rail_since"] < self.e_rail_wait.value():
            return False
        wd["rail_since"] = None
        wd["relocks"] = [x for x in wd["relocks"] if now - x < 3600]
        if len(wd["relocks"]) >= self.e_wd_max.value():
            if not wd.get("rail_limit_logged"):
                wd["rail_limit_logged"] = True
                self.hub.emit_log("WATCHDOG", f"PLL railed with the servo on, but {len(wd['relocks'])} relocks in "
                                              "the last hour already — not relocking")
            return False
        wd["rail_limit_logged"] = False
        wd["relocks"].append(now)
        wd["running"] = True
        out = d.get("pll_out_v")
        self._wd_state(f"relocking · PLL railed ({len(wd['relocks'])}/{self.e_wd_max.value()} this hour)", "warn")
        self.hub.emit_log("WATCHDOG", f"OPL #2 PLL output {out:.2f} V railed with the servo on — breaking the lock "
                                      "and relocking")
        self.start(from_watchdog=True)
        return True

    def _comb_pill(self):
        """Comb state from the Vescent Comb app's status file (read every 2 s)."""
        from ..comb_link import read_status, verdict
        st = read_status(self.settings)
        text, kind = verdict(st)
        self.pill_comb.set(text, kind)
        fresh = st.get("ok_file") and st.get("age_s", 1e9) < 10
        o1, fp, ff = st.get("opl1", {}), st.get("fpga", {}), st.get("ffc", {})

        def show(r, val, good, bad_txt):
            if not fresh or val is None:
                r.set("—")
            else:
                r.set(good if val else bad_txt, "{}", T.OK if val else T.WARN)
        show(self.r_frep, o1.get("frep_locked") if st.get("connected", {}).get("opl1") else None, "locked", "open")
        ph = fp.get("ceo_phase_rad")
        show(self.r_ceo, fp.get("ceo_locked"), "locked" + (f" · {ph:.2f} rad" if isinstance(ph, (int, float)) else ""),
             "open")
        show(self.r_ffc, ff.get("mode_locked"), "mode-locked", "not mode-locked")
        self.l_comb.setText(f"{st.get('path')} · " + (f"updated {st['age_s']:.0f} s ago" if st.get("ok_file")
                                                      else "not found: start the Vescent Comb app"))

    # ---- quick controls ------------------------------------------------------------------------------------
    def _grid(self):
        model = self.settings.get("ui.laser.model", "hp8168e")
        dflt = {"hp8168d": 0.1, "hp8168e": 0.01, "sws": 0.001}.get(model, 0.01)
        return float(self.settings.get(f"ui.laser.grid_nm.{model}", dflt))

    def _snap_wl(self):
        v = snap_to_grid(self.e_wl.value(), self._grid())
        self.e_wl.blockSignals(True)
        self.e_wl.setValue(v)
        self.e_wl.blockSignals(False)

    def _p_edited(self, which):
        if which == "dbm":
            dbm = round(self.e_dbm.value(), 2)
        else:
            w = self.e_w.value()
            dbm = round(w_to_dbm(w), 2) if w > 0 else self.e_dbm.value()
        self.e_dbm.blockSignals(True)
        self.e_dbm.setValue(dbm)
        self.e_dbm.blockSignals(False)
        self.e_w.setValue(dbm_to_w(dbm))

    def set_wl(self):
        self.pull.clear()
        self._snap_wl()
        v = self.e_wl.value()
        self.call(lambda d: d.set_wavelength_nm(v), log=f"wavelength {v:.3f} nm", role="laser")

    def set_pw(self):
        self.pull.clear()
        self._p_edited("dbm")
        dbm = self.e_dbm.value()
        self.call(lambda d: d.set_power_dbm(dbm) if hasattr(d, "set_power_dbm") else d.set_power(dbm, "dBm"),
                  log=f"power {dbm:.2f} dBm ({eng(dbm_to_w(dbm), 'W')})", role="laser")

    def laser_on(self):
        self.call(lambda d: d.output_on(), log="laser output ON", role="laser")

    def laser_off(self):
        self.call(lambda d: d.output_off(), log="laser output OFF", role="laser")

    def set_target(self):
        v = self.e_tgt.value() / 1e6
        self.call(lambda d: d.set_target_beatnote(v), log=f"OPL #2 target {eng(v * 1e6, 'Hz', 7)}", role="opl2")

    def set_servo(self, i):
        if i == 0:
            self._wd["user_off"] = True          # a hand-made servo-off disarms the watchdog until the next lock
        self.call(lambda d: d.set_servo(i == 1), log=f"OPL #2 servo {'ON' if i else 'OFF'}", role="opl2")

    def beat_check(self):
        if not self.hub.has("opl2"):
            return
        opl = self.hub.device("opl2")
        self.l_check.setText("checking…")

        def run():
            try:
                r = run_beat_check(self.hub, self.settings, opl)
            except Exception as e:
                r = e
            self.br.beat.emit(r)
        threading.Thread(target=run, daemon=True).start()

    def _beat_result(self, r):
        if isinstance(r, Exception):
            self.l_check.setText(f"check failed: {r}")
        elif r.note == scope_owner.BLOCKED_TEXT:
            self.l_check.setText(r.note)
        elif r.found and r.source == "OPL counter":
            self.l_check.setText(f"beat on the counter: {eng(r.freq_hz, 'Hz', 9)}")
        elif r.found:
            self.l_check.setText(f"{r.source}: {r.level_dbm:.0f} dBm at {eng(r.freq_hz, 'Hz', 7)} "
                                 f"({'+' if r.offset_hz >= 0 else '−'}{eng(abs(r.offset_hz), 'Hz', 4)} from target)")
        else:
            self.l_check.setText(f"no beat found ({r.source or 'no analyzer/scope connected'}) {r.note}")

    # ---- sequence -------------------------------------------------------------------------------------------
    def start(self, from_watchdog: bool = False):
        devs = {r: self.hub.device(r) for r in ("laser", "opl2", "scope", "sa") if self.hub.has(r)}
        self._wd["running"] = from_watchdog
        params = LaserLockParams(wavelength_nm=self.e_wl.value() if self.ck_wl.isChecked() and not from_watchdog
                                 else None,
                                 require_comb=self.ck_comb.isChecked(), enforce_limits=self.ck_lim.isChecked(),
                                 window_hz=self.e_win.value(), dwell_s=self.e_dwell.value(),
                                 scope_channel=beat_monitor.channel(self.settings),
                                 beat_role=beat_monitor.source(self.settings),
                                 scope_span_hz=beat_monitor.span_hz(self.settings),
                                 max_fwhm_hz=self.e_fmax.value(), dry_run=self.ck_dry.isChecked(),
                                 beat_near_hz=self.e_near.value(), beat_still_hz=self.e_still.value(),
                                 beat_still_s=self.e_still_s.value(), beat_timeout_s=self.e_btmo.value(),
                                 setpoint_check=not from_watchdog)       # a relock never stops to ask
        for r in self.rows.values():
            r.set("wait", " ")
        self.shist = W.History()
        self.seq = LaserLockSequence(devs, params, on_step=self.br.step.emit, on_log=self.br.log.emit,
                                     on_sample=self.br.sample.emit, ask=self._ask_blocking,
                                     comb_status=lambda: comb_locked(self.settings))
        self.pill_seq.set("running", "warn")
        self.b_start.setEnabled(False)
        self.b_stop.setEnabled(True)

        def run():
            ok = self.seq.run()
            self.br.finished.emit(ok)
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        if self.seq:
            self.seq.stop()

    def _on_step(self, st):
        self.rows[st.id].set(st.status, st.detail or " ")

    def _on_sample(self, s):
        """Monitor samples from the sequence: scope FWHM / offset trend and the live spectrum."""
        if s.get("fwhm_hz") is None:
            return
        self.shist.add(fwhm=s["fwhm_hz"], off=s["peak_off_hz"])
        tt, y = self.shist.series("fwhm")
        self.c_fwhm.setData(tt, y)
        tt, y = self.shist.series("off")
        self.c_poff.setData(tt, y)
        self.mon.show_result({**s, "source": "lock monitor"})      # the monitor panel shows the same capture

    def _finished(self, ok):
        self.pill_seq.set("laser locked" if ok else "stopped", "ok" if ok else "bad")
        if self._wd["running"]:
            self.hub.emit_log("WATCHDOG", "relock " + ("succeeded" if ok else "failed"))
        self._wd["running"] = False
        if ok:
            self._wd.update(locked_once=True, lost_since=None, user_off=False)
        self.b_start.setEnabled(True)
        self.b_stop.setEnabled(False)

    def _ask_blocking(self, q, rows=None):
        self._ask_evt.clear()
        self.br.ask.emit(q, rows)
        self._ask_evt.wait(600)
        return self._ask_ans

    def _ask_gui(self, q, rows):
        if isinstance(rows, dict) and rows.get("always"):
            self._ask_ans = _ask_always(self, "Laser lock", q, "Change")
        else:
            self._ask_ans = W.confirm(self, "Laser lock", q, "Yes")
        self._ask_evt.set()


def _ask_always(parent, title, text, ok_text) -> bool:
    """A question you asked for: shown even with Settings → "Ask before actions" off."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Question)
    ok = box.addButton(ok_text, QMessageBox.AcceptRole)
    box.addButton("Leave as is", QMessageBox.RejectRole)
    box.exec()
    return box.clickedButton() is ok
