"""Scope beat monitor — the same panel on the Laser lock and OPL #2 pages (no separate scope window).

Captures the beat channel (CH2 by default) around the OPL #2 target and shows the spectrum, a piece of
the waveform, and FWHM / peak offset / level / movement (std of the last peaks). Read only: nothing on
the scope or the OPL is changed. Channel and span are shared by both pages and by the lock monitor.

It captures only while it is on screen with "Live" ticked, and skips a capture while another feature
(lock monitor, auto-tune, beat check) holds the scope; the lock monitor feeds its own samples in.
"""
from __future__ import annotations

import collections
import math
import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from laserlock.core.units import eng
from laserlock.gui import theme as T
from laserlock.gui import widgets as W

from .. import scope_owner
from ..beat_check import beat_fwhm, spectrum_fwhm

KEY = "ui.beatmon"
SCOPE_USER = "Beat monitor"
WAVE_POINTS = 2000


def channel(settings) -> int:
    return int(settings.get(f"{KEY}.ch", 2) or 2)


def source(settings) -> str:
    """The beat instrument: "scope" (Rigol, FFT of CH2) or "sa" (HP 8563E spectrum analyzer)."""
    return "sa" if settings.get(f"{KEY}.source", "scope") == "sa" else "scope"


DEFAULT_SPAN_HZ = 70e6


def span_hz(settings) -> float:
    return float(settings.get(f"{KEY}.span_hz", DEFAULT_SPAN_HZ) or DEFAULT_SPAN_HZ)


class _Bridge(QObject):
    result = Signal(object)


class BeatMonitor(QWidget):
    def __init__(self, hub, settings, parent=None, title: str = "Beat monitor · scope"):
        super().__init__(parent)
        self.hub, self.settings = hub, settings
        self.br = _Bridge()
        self.br.result.connect(self.show_result)
        self._busy = False
        self._last = 0.0
        self.peaks = collections.deque(maxlen=10)

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.pill = W.Pill("—")
        p = W.Panel(title, self.pill)
        self.c_src = W.bind(settings, f"{KEY}.source", W.combo([("Oscilloscope (Rigol)", "scope"),
                                                               ("Spectrum analyzer (HP 8563E)", "sa")]), "scope")
        self.c_src.setToolTip("Which instrument watches the beat. Shared by both pages, the lock monitor and the "
                              "auto-tune.")
        self.c_ch = W.bind(settings, f"{KEY}.ch", W.combo([("CH2", 2), ("CH1", 1), ("CH3", 3), ("CH4", 4)]), 2)
        self.f_ch = W.field("Scope channel", self.c_ch)
        self.c_src.currentIndexChanged.connect(lambda _i: self._src_changed())
        if settings.get(f"{KEY}.span_hz") == 2e6 and not settings.get(f"{KEY}.span_70_migrated"):
            settings.set(f"{KEY}.span_hz", DEFAULT_SPAN_HZ)          # the old 2 MHz default → 70 MHz, once
        settings.set(f"{KEY}.span_70_migrated", True)
        self.e_span = W.bind(settings, f"{KEY}.span_hz", W.EngEdit(DEFAULT_SPAN_HZ, "Hz"), DEFAULT_SPAN_HZ)
        self.ck_live = W.bind(settings, f"{KEY}.live", QCheckBox("Live (1 s)"), True)
        p.add(W.hbox(W.field("Beat instrument", self.c_src), self.f_ch, W.field("Span around target", self.e_span),
                     self.ck_live,
                     W.button("Capture", "primary", self.capture), None))
        self.r_off = W.Readout("Peak − target", big=True)
        self.r_fwhm = W.Readout("FWHM", big=True)
        self.r_move = W.Readout("Movement (last 10)")
        self.r_lvl = W.Readout("Level")
        p.add(W.hbox(self.r_off, self.r_fwhm, self.r_move, self.r_lvl, None))
        plots = QHBoxLayout()
        self.spec = W.plot(220, "Power (linear, rel. to peak)", "Frequency (Hz)", title="beat_spectrum")
        self.c_spec = self.spec.plot(pen=W.pen(T.PLOT2, 1.2))
        self.c_spec.setDownsampling(auto=True, method="peak")
        self.c_spec.setClipToView(True)
        self.tline = pg.InfiniteLine(50e6, pen=pg.mkPen("#FFFFFF", style=Qt.DashLine))
        self.spec.addItem(self.tline, ignoreBounds=True)
        self.wave = W.plot(220, "Voltage (V)", "Time (s)", title="beat_waveform")
        self.c_wave = self.wave.plot(pen=W.pen(T.PLOT1, 1.0))
        self.c_wave.setDownsampling(auto=True, method="peak")
        self.c_wave.setClipToView(True)
        plots.addWidget(self.spec, 3)
        plots.addWidget(self.wave, 2)
        p.add(plots)
        self.l_note = W.label("", "mono")
        self.l_note.setWordWrap(True)
        p.add(self.l_note)
        v.addWidget(p)

        self._src_changed()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(250)

    # ---- capture -----------------------------------------------------------------------------------
    def _target_hz(self):
        t = self.hub.last("opl2").get("target_beatnote")
        return t * 1e6 if isinstance(t, (int, float)) and t > 0 else None

    def _tick(self):
        if (self.ck_live.isChecked() and self.isVisible() and not self._busy
                and time.time() - self._last >= 1.0):
            self.capture(quiet=True)

    def _src_changed(self):
        sa = self.c_src.currentData() == "sa"
        self.f_ch.setVisible(not sa)
        self.wave.setVisible(not sa)                       # an analyzer has no waveform to show
        self.peaks.clear()

    def capture(self, quiet: bool = False):
        if self._busy:
            return
        role = self.c_src.currentData() or "scope"
        if not self.hub.has(role):
            self.pill.set(("spectrum analyzer" if role == "sa" else "scope") + " not connected", "idle")
            return
        tgt = self._target_hz()
        if tgt is None:
            self.pill.set("OPL #2 target unknown", "idle")
            return
        if not scope_owner.acquire(SCOPE_USER):
            who = scope_owner.owner()
            self.pill.set(f"scope in use: {who}" if who else "scope busy", "idle")
            return
        self._busy, self._last = True, time.time()
        ch, span = self.c_ch.currentData() or 2, self.e_span.value()

        def work(d):                                     # on the instrument's worker thread
            if role == "sa":
                from ..beat_check import measure_beat_sa
                r = measure_beat_sa(d, tgt, span, trace=True)
                r.update(target_hz=tgt)
                return r
            t, v = d.capture(ch)
            r = beat_fwhm(t, v, tgt, span, trace=True)
            n = min(len(t), WAVE_POINTS)
            r.update(target_hz=tgt, t=np.asarray(t[:n]), v=np.asarray(v[:n]), fs=1.0 / float(t[1] - t[0]))
            return r

        def free():
            self._busy = False
            scope_owner.release(SCOPE_USER)

        def done(r):
            free()
            self.br.result.emit(r)

        def err(e):
            free()
            self.br.result.emit({"error": str(e)})
        self.hub.call(role, work, done, on_error=err)

    # ---- display (also fed by the lock monitor) -----------------------------------------------------
    def show_result(self, r: dict):
        if r.get("error"):
            self.pill.set("capture failed", "bad")
            self.l_note.setText(r["error"])
            return
        tgt = r.get("target_hz") or self._target_hz()
        if tgt:
            self.tline.setValue(tgt)
        if r.get("t") is not None:
            self.c_wave.setData(r["t"], r["v"])
        fw = r.get("fwhm_hz")
        if fw is None or not math.isfinite(fw):
            fs = r.get("fs")
            self.pill.set("no beat in span", "warn")
            self.l_note.setText("No beat found around the target" + (f" (sample rate {eng(fs, 'Sa/s')}: it must be "
                                "above twice the beat, with a long enough record for the span)" if fs else ""))
            for rd in (self.r_off, self.r_fwhm, self.r_lvl):
                rd.set(None)
            return
        if r.get("f") is not None:
            self.c_spec.setData(np.asarray(r["f"]), 10 ** (np.asarray(r["p_db"]) / 10))   # linear power
        pk = r["peak_hz"]
        off = pk - tgt if tgt else float("nan")
        self.peaks.append(pk)
        mv = float(np.std(self.peaks)) if len(self.peaks) >= 3 else None
        self.r_off.set(("+" if off >= 0 else "−") + eng(abs(off), "Hz", 4) if math.isfinite(off) else None)
        def num(x):
            return isinstance(x, (int, float)) and math.isfinite(x)
        rbw = r.get("rbw_hz")
        self.r_fwhm.set(eng(fw, "Hz", 3) + (f" (RBW {eng(rbw, 'Hz', 3)})" if num(rbw) else ""))
        self.r_move.set(eng(mv, "Hz", 3) if mv is not None else "…")
        if num(r.get("level_dbm")):
            self.r_lvl.set(f"{r['level_dbm']:.1f} dBm")
        else:
            self.r_lvl.set(f"{r['level_dbv']:.1f} dBV" if num(r.get("level_dbv")) else None)
        self.pill.set(r.get("source", "live"), "ok")
        self.l_note.setText(f"peak {eng(pk, 'Hz', 9)}" + (f" · fs {eng(r['fs'], 'Sa/s')}" if r.get("fs") else ""))
