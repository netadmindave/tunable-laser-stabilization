"""Tunable laser page — one page, model chosen from a dropdown of what the scan found.

Wavelength ↔ frequency and dBm ↔ W fields are linked: edit either and the other follows.
Wavelengths are rounded to the nearest step of the laser's tuning grid (up or down, whichever
is closer). The comb-tooth panel shows the tooth n the laser sits next to.
"""
from __future__ import annotations

import os
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QComboBox, QGridLayout

from laserlock.addonkit import REGISTRY
from laserlock.core.units import C_LIGHT, dbm_to_w, eng, nm_to_thz, snap_to_grid, thz_to_nm, w_to_dbm
from laserlock.dsp import peak_frequency_fft
from laserlock.gui import theme as T
from laserlock.gui import widgets as W
from laserlock.gui.options_panel import OptionsPanel
from laserlock.gui.page_base import Page
from laserlock.settings import default_data_dir
from ..comb_tooth import laser_sigma_hz, nearest_tooth
from ..hp8168 import GRID_CHOICES_NM, MODEL_SPECS
from ..laser_setpoints import FieldPull

MODELS = {
    "hp8168d": dict(name="HP 8168D", kind="hp8168", range="1480 – 1570 nm", grid_nm=0.100, acc_nm=0.2,
                    power="10 nW – 1.6 mW", coh="AM source INT2 (keep OFF)", sweep="software step + dwell"),
    "hp8168e": dict(name="HP 8168E", kind="hp8168", range="1475 – 1575 nm", grid_nm=0.010, acc_nm=0.1,
                    power="10 nW – 1.6 mW", coh="AM source INT2 (keep OFF)", sweep="software step + dwell"),
    "sws": dict(name="JDSU SWS17101 (TUNICS)", kind="sws17101", range="1500 – 1640 nm (per unit)", grid_nm=0.001,
                acc_nm=0.1, power="≤ +10 dBm", coh="COHCTL · write-only", sweep="software step · SPEED"),
}


class _Bridge(QObject):
    progress = Signal(int, int, float)
    done = Signal(str)


class LaserPage(Page):
    TITLE = "Laser"
    ROLE = "laser"

    def __init__(self, hub, settings, main=None):
        super().__init__(hub, settings, main)
        k = "ui.laser"
        self.pill_out = W.Pill("—")
        self.c_model = QComboBox()
        self.c_model.setMinimumWidth(420)
        self.c_model.activated.connect(self.choose_model)
        self.header("Tunable laser", "", [self.pill_out],
                    [W.button("Restore last session…", slot=self.restore_last_session),
                     W.button("Rescan GPIB", slot=lambda: self.main and self.main.open_finder())])
        self.v.addLayout(W.hbox(W.field("Laser model", self.c_model), None))
        self.l_idn = W.label("", "mono")
        self.v.addWidget(self.l_idn)

        caps = QGridLayout()
        self.cap = {}
        for i, (key, cap) in enumerate((("range", "Range"), ("grid", "Tuning step"), ("power", "Power"),
                                        ("coh", "Coherence control"), ("sweep", "Sweep"))):
            r = W.Readout(cap)
            r.setStyleSheet(f"background:{T.CHROME}; border:1px solid #232A33; border-radius:6px; padding:6px;")
            self.cap[key] = r
            caps.addWidget(r, 0, i)
        self.v.addLayout(caps)

        g = QGridLayout()
        g.setSpacing(14)
        self.v.addLayout(g)
        # ---- output -----------------------------------------------------------------------------
        p = W.Panel("Output")
        self.b_off = W.button("Output OFF", "danger", self.output_off)
        self.b_on = W.button("Output ON", "primary", self.output_on)
        p.add(W.hbox(self.b_off, self.b_on, None))
        p.add(W.label("Output goes OFF at the end of a scan, on Safe standby and when the app closes.", "hint"))
        g.addWidget(p, 0, 0)

        # ---- wavelength ↔ frequency -------------------------------------------------------------------
        p = W.Panel("Wavelength ↔ frequency")
        self.r_wl = W.Readout("Actual wavelength", big=True)
        self.r_nu = W.Readout("Actual frequency", big=True)
        p.add(W.hbox(self.r_wl, self.r_nu, None))
        self.e_wl = W.dspin(1550.0, 1400, 1700, 4, 0.01, "nm")          # filled from the laser
        self.e_nu = W.dspin(nm_to_thz(1550.0), 170, 215, 6, 0.001, "THz")
        self.e_wl.editingFinished.connect(lambda: self._wl_edited("wl"))
        self.e_nu.editingFinished.connect(lambda: self._wl_edited("nu"))
        self.c_grid = W.combo([(f"{g_ * 1e3:g} pm", g_) for g_ in GRID_CHOICES_NM])
        self.c_grid.activated.connect(self.set_grid)
        p.add(W.grid([W.field("Wavelength", self.e_wl), W.field("Frequency", self.e_nu),
                      W.field("Tuning step", self.c_grid)], 3))
        self.l_snap = W.label("", "lbl", wrap=True)
        p.add(self.l_snap)
        p.add(W.hbox(W.button("Set", "primary", self.set_wl), W.button("− 1 step", slot=lambda: self.step(-1)),
                     W.button("+ 1 step", slot=lambda: self.step(1)), None))
        g.addWidget(p, 0, 1)

        # ---- power dBm ↔ W -----------------------------------------------------------------------------
        p = W.Panel("Power dBm ↔ W")
        self.r_pdbm = W.Readout("Actual", big=True)
        self.r_pw = W.Readout("Actual", big=True)
        p.add(W.hbox(self.r_pdbm, self.r_pw, None))
        self.e_dbm = W.dspin(0.0, -60, 13, 2, 0.1, "dBm")                # filled from the laser
        self.e_w = W.EngEdit(dbm_to_w(0.0), "W")
        self.e_dbm.editingFinished.connect(lambda: self._p_edited("dbm"))
        self.e_w.editingFinished.connect(lambda: self._p_edited("w"))
        p.add(W.grid([W.field("Power", self.e_dbm), W.field("= ", self.e_w)], 2))
        p.add(W.hbox(W.button("Set", "primary", self.set_power), None))
        g.addWidget(p, 1, 0)
        self.pull = FieldPull(self.e_wl, self.e_nu, self.e_dbm, self.e_w)

        # ---- comb tooth ----------------------------------------------------------------------------------
        self.pill_tooth = W.Pill("—")
        p = W.Panel("Comb tooth", self.pill_tooth)
        self.e_frep = W.bind(settings, f"{k}.comb.frep_hz", W.EngEdit(100e6, "Hz"), 100e6)
        self.c_ceo = W.bind(settings, f"{k}.comb.ceo_src", W.combo([("Comb app (FPGA CEO reference)", "fpga"),
                                                                    ("typed in", "manual")]), "fpga")
        self.e_ceo = W.bind(settings, f"{k}.comb.fceo_hz", W.EngEdit(20e6, "Hz"), 20e6)
        self.c_sign = W.bind(settings, f"{k}.comb.sign", W.combo([("+ f_ceo", 1), ("− f_ceo", -1)]), 1)
        self.e_known = W.bind(settings, f"{k}.comb.known_hz", W.EngEdit(0.0, "Hz"), 0.0)
        for w_ in (self.e_frep, self.e_ceo, self.e_known):
            w_.editingFinished.connect(self._update_tooth)
        for w_ in (self.c_ceo, self.c_sign):
            w_.currentIndexChanged.connect(lambda *_: self._update_tooth())
        p.add(W.grid([W.field("f_rep", self.e_frep), W.field("f_ceo from", self.c_ceo),
                      W.field("f_ceo", self.e_ceo), W.field("Sign", self.c_sign),
                      W.field("Wavemeter ν (0 = use laser)", self.e_known)], 3))
        self.r_n = W.Readout("Tooth n", big=True)
        self.r_nun = W.Readout("Tooth frequency ν_n")
        self.r_off = W.Readout("Laser − tooth")
        self.r_eb = W.Readout("Expected beat")
        self.r_mb = W.Readout("OPL #2 beat (measured)")
        self.r_side = W.Readout("Laser if locked")
        p.add(W.grid([self.r_n, self.r_nun, self.r_off, self.r_eb, self.r_mb, self.r_side], 3))
        self.l_tooth = W.label("", "hint")
        p.add(self.l_tooth)
        g.addWidget(p, 1, 1)

        # ---- scan ------------------------------------------------------------------------------------------
        key = f"{k}.scan"
        self.pill_scan = W.Pill("idle")
        p = W.Panel("Stepped scan", self.pill_scan)
        self.s_a = W.bind(settings, f"{key}.start", W.dspin(1545, 1400, 1700, 3, 0.1, "nm"), 1545)
        self.s_b = W.bind(settings, f"{key}.stop", W.dspin(1555, 1400, 1700, 3, 0.1, "nm"), 1555)
        self.s_step = W.bind(settings, f"{key}.step", W.dspin(0.1, 0.001, 50, 3, 0.01, "nm"), 0.1)
        self.s_dwell = W.bind(settings, f"{key}.dwell", W.EngEdit(0.5, "s"), 0.5)
        self.s_rec = W.combo([])
        self._fill_record_choices()
        self.s_rec.currentIndexChanged.connect(lambda i: self.settings.set(f"{key}.record", self.s_rec.itemData(i)))
        p.add(W.grid([W.field("Start", self.s_a), W.field("Stop", self.s_b), W.field("Step", self.s_step),
                      W.field("Dwell", self.s_dwell), W.field("Record at each step", self.s_rec)], 3))
        self.b_scan = W.button("Run scan", "primary", self.run_scan)
        self.b_sstop = W.button("Stop", slot=self.stop_scan)
        self.l_scan = W.label("", "lbl")
        p.add(W.hbox(self.b_scan, self.b_sstop, self.l_scan, None))
        g.addWidget(p, 2, 0)
        # ---- comb lock link ---------------------------------------------------------------------------------
        self.pill_lock = W.Pill("—")
        p = W.Panel("Lock to comb · SLICE-OPL #2 → Brimrose AOM", self.pill_lock)
        self.l_lock = W.label("", "lbl", wrap=True)
        p.add(self.l_lock)
        p.add(W.hbox(W.button("Open OPL #2", slot=lambda: self.main and self.main.show_page("opl2")),
                     W.button("Laser lock page", slot=lambda: self.main and self.main.show_page("laserlock")), None))
        g.addWidget(p, 2, 1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)

        p = W.Panel("All instrument options")
        self.opts = OptionsPanel(hub, self.ROLE, columns=3,
                                 intro="Every setting the connected laser exposes over GPIB (written and read back).")
        p.add(self.opts)
        self.v.addWidget(p)
        self.v.addStretch(1)

        self.bridge = _Bridge()
        self.bridge.progress.connect(lambda i, n, wl: self.l_scan.setText(f"{i}/{n} · {wl:.3f} nm"))
        self.bridge.done.connect(self._scan_done)
        self.stop_evt = threading.Event()
        self.model_key = settings.get(f"{k}.model", "hp8168e")
        self.actual = {"nu_hz": None, "beat_hz": None, "fceo_fpga": None}
        self._apply_model_ui()
        self._wl_edited("wl")
        self._p_edited("dbm")

    # ---- model -------------------------------------------------------------------------------------------
    @property
    def grid_nm(self) -> float:
        m = MODELS.get(self.model_key, MODELS["hp8168e"])
        return float(self.settings.get(f"ui.laser.grid_nm.{self.model_key}", m["grid_nm"]))

    def on_devices_changed(self):
        self._fill_record_choices()
        self.c_model.clear()
        scan = self.hub.scan
        found_keys = set()
        if scan:
            for f in scan.found:
                if f.kind == "hp8168":
                    key = "hp8168e" if "8168E" in f.model.upper() else "hp8168d"
                elif f.kind == "sws17101":
                    key = "sws"
                else:
                    continue
                found_keys.add(key)
                self.c_model.addItem(f"{MODELS[key]['name']} · SN {f.serial} · {f.address} (found)", (key, f.serial))
        for key, m in MODELS.items():
            if key not in found_keys:
                self.c_model.addItem(f"{m['name']} · not found on scan", (key, None))
        mine = self.hub.found.get(self.ROLE)
        if mine:
            key = "sws" if mine.kind == "sws17101" else ("hp8168e" if "8168E" in mine.model.upper() else "hp8168d")
            self.model_key = key
            for i in range(self.c_model.count()):
                if self.c_model.itemData(i) == (key, mine.serial):
                    self.c_model.setCurrentIndex(i)
            self.l_idn.setText(f"*IDN? → {mine.raw}")
            g_ = self.grid_nm
            self.call(lambda d: setattr(d, "grid_nm", g_))
            self.call(lambda d: d.snapshot(), lambda s: self.settings.save_device_state(self.ROLE, {
                k: v for k, v in s.items() if isinstance(v, (int, float, str, bool))}))
        else:
            self.l_idn.setText("no laser connected")
        self._apply_model_ui()

    def choose_model(self, i):
        key, serial = self.c_model.itemData(i)
        self.model_key = key
        self.settings.set("ui.laser.model", key)
        self._apply_model_ui()
        if serial is not None and self.main:
            self.main.assign_unit(self.ROLE, MODELS[key]["kind"], serial)

    def _apply_model_ui(self):
        m = MODELS.get(self.model_key, MODELS["hp8168e"])
        for key, r in self.cap.items():
            r.set(f"{self.grid_nm * 1e3:g} pm" if key == "grid" else m[key])
        W.set_combo_data(self.c_grid, self.grid_nm)
        self.c_grid.setEnabled(m["kind"] == "hp8168")
        self._wl_edited("wl")

    def set_grid(self, i):
        g_ = self.c_grid.itemData(i)
        self.settings.set(f"ui.laser.grid_nm.{self.model_key}", g_)
        self.call(lambda d: setattr(d, "grid_nm", g_), log=f"tuning step {g_ * 1e3:g} pm")
        self._apply_model_ui()

    # ---- linked fields ---------------------------------------------------------------------------------
    def _wl_edited(self, which):
        g_ = self.grid_nm
        req = self.e_wl.value() if which == "wl" else thz_to_nm(self.e_nu.value())
        wl = snap_to_grid(req, g_)
        for w_, val in ((self.e_wl, wl), (self.e_nu, nm_to_thz(wl))):
            w_.blockSignals(True)
            w_.setValue(val)
            w_.blockSignals(False)
        self.settings.set("ui.laser.set_nm", wl)
        moved = abs(req - wl) > 1e-9
        self.l_snap.setText((f"Requested {req:.4f} nm → rounded to {wl:.3f} nm" if moved else f"{wl:.3f} nm")
                            + f" · {eng(nm_to_thz(wl) * 1e12, 'Hz', 9)} · step {g_ * 1e3:g} pm "
                            f"≈ {eng(C_LIGHT * g_ * 1e-9 / (wl * 1e-9) ** 2, 'Hz', 3)}")

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
        self.settings.set("ui.laser.set_dbm", dbm)

    # ---- polls -------------------------------------------------------------------------------------------
    def on_poll(self, role, d):
        if role == "opl2":
            b = d.get("beatnote")
            has = isinstance(b, float) and b > 1
            servo = d.get("servo_on")
            self.actual["beat_hz"] = b * 1e6 if has else None
            lo, hi, out = d.get("pll_min"), d.get("pll_max"), d.get("pll_out_v")
            ok_out = all(isinstance(x, float) for x in (lo, hi, out)) and hi > lo and \
                lo + 0.05 * (hi - lo) < out < hi - 0.05 * (hi - lo)
            locked = bool(servo) and ok_out          # the OPL #2 counter may never see the beat
            self.pill_lock.set("locked" if locked else ("servo on · PLL on the rail" if servo else "servo off"),
                               "ok" if locked else ("warn" if servo else "idle"))
            self.l_lock.setText(f"Counter {'reads ' + eng(b * 1e6, 'Hz', 7) if has else 'sees no beat'}; "
                                f"servo {'on' if servo else 'off'}. Beat check and auto-tune are on the OPL #2 page.")
            self._update_tooth()
            return
        if role != self.ROLE:
            return
        on = d.get("output_on")
        self.pill_out.set("Output on" if on else "Output off", "warn" if on else "idle")
        wl = d.get("wavelength_nm")
        self.r_wl.set(f"{wl:.3f} nm" if isinstance(wl, (int, float)) else None)
        nu = C_LIGHT / (wl * 1e-9) if isinstance(wl, (int, float)) and wl > 0 else None
        self.actual["nu_hz"] = nu
        self.r_nu.set(eng(nu, "Hz", 8) if nu else None)
        pw = d.get("power_w")
        self.r_pdbm.set(f"{w_to_dbm(pw):.2f} dBm" if pw else None)
        self.r_pw.set_si(pw, "W", 4)
        if self.pull.free():                     # entry fields follow the laser unless you are editing them
            vals = []
            if isinstance(wl, (int, float)) and wl > 0:
                vals += [(self.e_wl, float(wl)), (self.e_nu, nm_to_thz(wl))]
            if isinstance(pw, (int, float)) and pw > 0:
                vals.append((self.e_dbm, round(w_to_dbm(pw), 2)))
            for w_, val in vals:
                w_.blockSignals(True)
                w_.setValue(val)
                w_.blockSignals(False)
            if isinstance(pw, (int, float)) and pw > 0:
                self.e_w.setValue(pw)
        self.b_on.setEnabled(not on)
        self._update_tooth()

    def _fceo(self):
        from ..comb_link import fceo_hz
        ref = fceo_hz(self.settings) if self.c_ceo.currentData() == "fpga" else None
        if ref:
            f = ref
        else:
            f = self.e_ceo.value()
        return f * (self.c_sign.currentData() or 1)

    def _update_tooth(self):
        known = self.e_known.value()
        nu = known if known > 0 else self.actual["nu_hz"]
        frep = self.e_frep.value()
        if not nu or frep <= 0:
            for r in (self.r_n, self.r_nun, self.r_off, self.r_eb, self.r_side):
                r.set(None)
            self.pill_tooth.set("laser not read", "idle")
            return
        m = MODELS.get(self.model_key, MODELS["hp8168e"])
        sigma = None if known > 0 else laser_sigma_hz(nu, m["acc_nm"])
        t = nearest_tooth(nu, frep, self._fceo(), sigma, self.actual["beat_hz"])
        self.r_n.set(f"{t.n:,}" + (f" ± {t.n_uncertainty}" if t.n_uncertainty else ""))
        self.r_nun.set(eng(t.nu_n_hz, "Hz", 12) + f" · {t.lambda_n_nm:.4f} nm")
        self.r_off.set(("+" if t.offset_hz >= 0 else "−") + eng(abs(t.offset_hz), "Hz", 5))
        self.r_eb.set(eng(t.expected_beat_hz, "Hz", 5))
        self.r_mb.set(eng(t.measured_beat_hz, "Hz", 7) if t.measured_beat_hz else "no beat")
        if t.measured_beat_hz:
            self.r_side.set(f"{eng(t.laser_hz_if_below, 'Hz', 12)} or {eng(t.laser_hz_if_above, 'Hz', 12)}")
        else:
            self.r_side.set(None)
        src = "wavemeter value" if known > 0 else f"laser readback (±{m['acc_nm']:g} nm absolute)"
        self.pill_tooth.set(f"n = {t.n:,}", "ok" if (t.n_uncertainty or 0) == 0 else "warn")
        self.l_tooth.setText(f"ν_n = n·f_rep + f_ceo, n from the {src}. "
                             + (f"The ±{t.n_uncertainty} comes from that accuracy; a wavemeter reading pins n. "
                                if t.n_uncertainty else "")
                             + "With a beat on OPL #2 the laser is at ν_n ± the beat (side set by the OPL sign).")

    # ---- actions -----------------------------------------------------------------------------------------
    def output_on(self):
        self.call(lambda d: d.output_on(), log="output ON")

    def output_off(self):
        self.call(lambda d: d.output_off(), log="output OFF")

    def set_wl(self):
        self.pull.clear()
        self._wl_edited("wl")
        wl = self.e_wl.value()
        self.call(lambda d: d.set_wavelength_nm(wl), lambda r: self.remember_state(),
                  log=f"λ {wl:.3f} nm ({eng(nm_to_thz(wl) * 1e12, 'Hz', 9)})")

    def step(self, n):
        self.call(lambda d: d.step(n), log=f"step {n:+d} × {self.grid_nm * 1e3:g} pm")

    def set_power(self):
        self.pull.clear()
        self._p_edited("dbm")
        dbm = self.e_dbm.value()

        def work(d):
            if hasattr(d, "set_power_dbm"):
                return d.set_power_dbm(dbm)
            return d.set_power(dbm, "dBm")
        self.call(work, lambda r: self.remember_state(), log=f"power {dbm:.2f} dBm ({eng(dbm_to_w(dbm), 'W')})")

    # ---- scan ---------------------------------------------------------------------------------------------
    def run_scan(self):
        if not self.connected:
            return
        a, b, st, dw, rec = (self.s_a.value(), self.s_b.value(), self.s_step.value(), self.s_dwell.value(),
                             self.s_rec.currentData())
        laser = self.hub.device(self.ROLE)
        opl2 = self.hub.device("opl2")
        kind, _, rrole = (rec or "none").partition(":")
        other = self.hub.device(rrole) if rrole else None
        folder = os.path.join(self.settings.get("ui.data_dir") or str(default_data_dir()), "laser")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"laser_scan_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        self.stop_evt.clear()
        n = int(np.floor((b - a) / st + 0.5)) + 1
        self.pill_scan.set("running", "warn")

        def record(wl):
            if rec == "power":
                return laser.poll().get("power_w")
            if rec == "opl2" and opl2 is not None:
                bn = opl2.read_beatnote()
                return bn * 1e6 if isinstance(bn, (int, float)) else bn
            if kind == "scope" and other is not None:          # any scope add-on, CH1
                t, v = other.capture(1)
                return peak_frequency_fft(v, float(t[1] - t[0]))
            if kind == "osa" and other is not None:            # any optical-spectrum add-on: peak wavelength
                wl_, pw = other.sweep_and_fetch()
                return float(wl_[int(np.argmax(pw))])
            if kind == "meter" and other is not None:          # any meter add-on
                return other.read()
            return None

        rec_name = {"power": "power_w", "opl2": "opl2_beat_hz", "none": "nothing"}.get(rec, f"{kind}_{rrole}")
        if kind == "scope":
            rec_name = f"{rrole}_peak_hz"
        elif kind == "osa":
            rec_name = f"{rrole}_peak_nm"
        elif kind == "meter":
            rec_name = f"{rrole}_reading"

        def run():
            i = [0]

            def cb(wl):
                i[0] += 1
                self.bridge.progress.emit(i[0], n, wl or 0)
                return record(wl)
            try:
                rows = laser.stepped_sweep(a, b, st, dw, cb, self.stop_evt)
                from laserlock.datafile import write_csv
                write_csv(path, ["wavelength_nm", rec_name], rows=rows, kind="laser stepped scan",
                          meta={"scan": {"start_nm": a, "stop_nm": b, "step_nm": st, "dwell_s": dw, "record": rec}})
                self.bridge.done.emit(f"{len(rows)} points → {path}")
            except Exception as e:
                self.bridge.done.emit(f"scan failed: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _fill_record_choices(self):
        items = [("Nothing (move only)", "none"), ("Power readback", "power"), ("OPL #2 beat frequency", "opl2")]
        for cap, kind, what in (("scope", "scope", "peak frequency, CH1"), ("optical_spectrum", "osa", "peak wavelength"),
                                ("meter", "meter", "reading")):
            for r in REGISTRY.roles_with(cap):
                items.append((f"{REGISTRY.role_label(r)} {what}", f"{kind}:{r}"))
        self.s_rec.blockSignals(True)
        self.s_rec.clear()
        for label, data in items:
            self.s_rec.addItem(label, data)
        W.set_combo_data(self.s_rec, self.settings.get("ui.laser.scan.record", "none"))
        self.s_rec.blockSignals(False)

    def stop_scan(self):
        self.stop_evt.set()

    def _scan_done(self, msg):
        self.pill_scan.set("done", "ok" if "failed" not in msg else "bad")
        self.l_scan.setText(msg)
        self.hub.emit_log("LASER", msg)
