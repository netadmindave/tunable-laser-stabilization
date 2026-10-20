"""SLICE-OPL #2 (laser → comb, drives the Brimrose AOM): the comb module's OPL page plus a beat check.

The beat check only looks (counter, then the scope); it never moves the OPL target. It is off while
the Rigol window is open."""
from __future__ import annotations

import threading
import time

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from laserlock.addonkit import REGISTRY
from laserlock.core.units import eng
from laserlock.gui import theme as T
from laserlock.gui import widgets as W
from .opl import OPLPage

from ..beat_check import BeatCheckConfig, BeatResult, verify_beat
from .. import scope_owner

SCOPE_USER = "OPL #2 beat check"


def beat_instruments(hub):
    """[(label, role, kind)] of every installed analyzer / scope add-on, connected or not."""
    out = []
    for cap, kind in (("spectrum", "sa"), ("scope", "scope")):
        for r in REGISTRY.roles_with(cap):
            f = hub.found.get(r)
            label = REGISTRY.role_label(r) + (f" · {f.model}" if f else "")
            out.append((label + ("" if hub.has(r) else " — not connected"), r, kind))
    return out


def beat_config(settings, role_key: str = "ui.opl2.beatcheck") -> BeatCheckConfig:
    k = role_key
    c = settings.get(f"{k}.center_hz")
    if c is None:                                  # settings from before v0.4 were in MHz
        c = (settings.get(f"{k}.center_mhz", 0) or 0) * 1e6
    span = settings.get(f"{k}.span_hz")
    if span is None:
        span = (settings.get(f"{k}.span_mhz", 20) or 20) * 1e6
    inst_role = settings.get(f"{k}.instrument")
    kind = "scope" if inst_role in REGISTRY.roles_with("scope") else "sa"
    return BeatCheckConfig(source=kind, center_hz=c if c > 0 else None,
                           span_hz=span, rbw_hz=settings.get(f"{k}.rbw", 1e5),
                           min_dbm=settings.get(f"{k}.min_dbm", -60), scope_channel=settings.get(f"{k}.scope_ch", 2),
                           every_s=settings.get(f"{k}.every_s", 10))


def run_beat_check(hub, settings, opl):
    """Counter first, then the chosen analyzer/scope (or any connected one). Blocking."""
    cfg = beat_config(settings)
    chosen = settings.get("ui.opl2.beatcheck.instrument")
    sa_roles = [r for r in REGISTRY.roles_with("spectrum") if hub.has(r)]
    sc_roles = [r for r in REGISTRY.roles_with("scope") if hub.has(r)]
    sa_role = chosen if chosen in sa_roles else (sa_roles[0] if sa_roles else None)
    sc_role = chosen if chosen in sc_roles else (sc_roles[0] if sc_roles else None)
    got = False
    if sc_role and not (sa_role and cfg.source == "sa"):
        if opl.has_beat():                         # counter sees it: no scope needed
            sc_role = None
        elif scope_owner.acquire(SCOPE_USER):
            got = True
        else:
            t = opl.get_target_beatnote()
            return BeatResult(False, "", target_hz=(t or 0.0) * 1e6, note=scope_owner.blocked_reason(SCOPE_USER))
    try:
        return verify_beat(opl, hub.device(sa_role) if sa_role else None, hub.device(sc_role) if sc_role else None,
                           cfg, sa_name=REGISTRY.role_label(sa_role) if sa_role else "",
                           scope_name=(REGISTRY.role_label(sc_role) + " FFT") if sc_role else "")
    finally:
        if got:
            scope_owner.release(SCOPE_USER)


class _BeatBridge(QObject):
    beat = Signal(object)


class OPL2Page(OPLPage):
    ROLE = "opl2"
    TITLE_TEXT = "SLICE-OPL #2 · laser → comb"
    LOCK_HINT = ("Brimrose driver tuning input is 7–14 V; the OPL reaches ±12 V. Keep PLLMIN 7.0, PLLMAX 12.0 so the "
                 "output never leaves the driver's range (≈ −50 to +21 MHz of AOM tuning if the input is linear).")
    DEFAULT_SCOPE_CH = 2
    REQUIRE_COUNTER_BEAT = False

    def __init__(self, hub, settings, main=None, role: str = None):
        self.bb = _BeatBridge()
        super().__init__(hub, settings, main, role)
        self.bb.beat.connect(self._beat_result)
        self.beat_timer = QTimer(self)
        self.beat_timer.timeout.connect(self._auto_beat_check)
        self.beat_timer.start(1000)
        self._beat_last = 0.0

    def extra_tabs(self):
        from .beat_monitor import BeatMonitor
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 0)
        self.mon = BeatMonitor(self.hub, self.settings)     # same panel as on the Laser lock page
        v.addWidget(self.mon)
        v.addStretch(1)
        return [(w, "Beat monitor (scope)"), (self._beat_tab(), "Beat check")]

    def _beat_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 10, 0, 0)
        key = f"ui.{self.ROLE}.beatcheck"
        self.pill_check = W.Pill("not checked")
        p = W.Panel("Beat check", self.pill_check)
        self.bc_enable = W.bind(self.settings, f"{key}.enabled",
                                QCheckBox("When the OPL shows no beat, verify with another instrument"), True)
        p.add(self.bc_enable)
        self.bc_inst = W.combo([])
        self.bc_inst.currentIndexChanged.connect(lambda i: self.settings.set(f"{key}.instrument", self.bc_inst.itemData(i)))
        p.add(W.field("Verify with (any spectrum-analyzer or scope add-on)", self.bc_inst))
        self.bc_center = W.bind(self.settings, f"{key}.center_hz", W.EngEdit(0.0, "Hz"), 0.0)
        self.bc_center.setToolTip("0 Hz = use the OPL target")
        self.bc_span = W.bind(self.settings, f"{key}.span_hz", W.EngEdit(20e6, "Hz"), 20e6)
        self.bc_rbw = W.bind(self.settings, f"{key}.rbw", W.combo([("1 kHz", 1e3), ("3 kHz", 3e3), ("10 kHz", 1e4),
                                                                   ("30 kHz", 3e4), ("100 kHz", 1e5), ("300 kHz", 3e5),
                                                                   ("1 MHz", 1e6)]), 1e5)
        self.bc_min = W.bind(self.settings, f"{key}.min_dbm", W.dspin(-60, -150, 30, 1, 1, "dBm"), -60)
        self.bc_ch = W.bind(self.settings, f"{key}.scope_ch", W.combo([("CH2", 2), ("CH1", 1), ("CH3", 3), ("CH4", 4)]), 2)
        self.bc_every = W.bind(self.settings, f"{key}.every_s", W.dspin(10, 1, 3600, 0, 1, "s"), 10)
        p.add(W.grid([W.field("Centre (0 = target)", self.bc_center), W.field("Span", self.bc_span),
                      W.field("RBW (analyzer)", self.bc_rbw), W.field("Min peak", self.bc_min),
                      W.field("Scope channel", self.bc_ch), W.field("Check every", self.bc_every)], 3))
        self.b_check_now = W.button("Check now", "primary", self.beat_check_now)
        self.l_bc_block = W.label("", "hint")
        p.add(W.hbox(self.b_check_now, self.l_bc_block, None))
        self.bc_plot = W.plot(170, "Level (dBm)", "Frequency (Hz)", title="beat_check")
        self.c_bc = self.bc_plot.plot(pen=W.pen(T.PLOT2))
        p.add(self.bc_plot)
        self.l_bc = W.label("", "mono")
        self.l_bc.setWordWrap(True)
        p.add(self.l_bc)
        v.addWidget(p)
        v.addStretch(1)
        self.last_beat = None
        return w

    def on_scope_owner(self):
        super().on_scope_owner()
        if hasattr(self, "b_check_now"):
            blocked = scope_owner.window_open()
            self.b_check_now.setEnabled(not blocked)
            self.l_bc_block.setText(scope_owner.BLOCKED_TEXT if blocked else "")

    def on_devices_changed(self):
        super().on_devices_changed()
        self.bc_inst.blockSignals(True)
        self.bc_inst.clear()
        items = beat_instruments(self.hub)
        for label, role, _ in items:
            self.bc_inst.addItem(label, role)
        if not items:
            self.bc_inst.addItem("no analyzer or scope add-on installed", None)
        W.set_combo_data(self.bc_inst, self.settings.get(f"ui.{self.ROLE}.beatcheck.instrument"))
        self.bc_inst.blockSignals(False)

    def beat_check_now(self):
        if not self.connected or scope_owner.window_open():
            return
        opl = self.hub.device(self.ROLE)
        self._beat_last = time.time()
        self.pill_check.set("checking…", "idle")

        def run():
            try:
                r = run_beat_check(self.hub, self.settings, opl)
            except Exception as e:
                r = e
            self.bb.beat.emit(r)
        threading.Thread(target=run, daemon=True).start()

    def _auto_beat_check(self):
        if not self.connected or not self.bc_enable.isChecked():
            return
        if getattr(self, "_has_beat", True) or time.time() - self._beat_last < self.bc_every.value():
            return
        if scope_owner.blocked_reason(SCOPE_USER):        # Rigol window open or the lock monitor is capturing
            return
        self.beat_check_now()

    def _beat_result(self, r):
        if isinstance(r, Exception):
            self.pill_check.set("check failed", "bad")
            self.l_bc.setText(str(r))
            return
        self.last_beat = r
        if r.trace_f is not None:
            self.c_bc.setData(np.asarray(r.trace_f), np.asarray(r.trace_p))
        now = time.strftime("%H:%M:%S")
        if r.found and r.source == "OPL counter":
            self.pill_check.set("beat on counter", "ok")
            self.l_bc.setText(f"{now} · counter reads {eng(r.freq_hz, 'Hz', 9)}")
        elif r.found:
            self.pill_check.set("beat found by analyzer", "ok")
            self.l_bc.setText(f"{now} · {r.source} peak {r.level_dbm:.0f} dBm at {eng(r.freq_hz, 'Hz', 7)} "
                              f"({'+' if r.offset_hz >= 0 else '−'}{eng(abs(r.offset_hz), 'Hz', 4)} from target) → "
                              "beat present, OPL counter not seeing it. "
                              "Check beat path / N1 / input level.")
        elif r.note == scope_owner.BLOCKED_TEXT:
            self.pill_check.set("scope in use", "idle")
            self.l_bc.setText(f"{now} · {r.note}")
            return
        else:
            self.pill_check.set("no beat found", "bad")
            self.l_bc.setText(f"{now} · no beat above {self.bc_min.value():.0f} dBm ({r.source or 'no analyzer'}) {r.note}")
        self.hub.emit_log(self.ROLE.upper(), self.l_bc.text())
