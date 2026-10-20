"""When an OPL counter shows no beat, look for it with the spectrum analyzer or scope."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

import numpy as np

from laserlock.dsp import peak_frequency_fft


@dataclass
class BeatCheckConfig:
    source: str = "scope"          # "scope" (FFT of a Rigol capture); "sa" kept for scripts with an analyzer
    center_hz: Optional[float] = None   # None -> OPL target
    span_hz: float = 20e6
    rbw_hz: float = 100e3
    min_dbm: float = -60.0
    scope_channel: int = 2
    every_s: float = 10.0
    offer_retarget: bool = False

    def as_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        c = cls()
        for k, v in (d or {}).items():
            if hasattr(c, k):
                setattr(c, k, v)
        return c


@dataclass
class BeatResult:
    found: bool
    source: str = ""
    freq_hz: float = float("nan")
    level_dbm: float = float("nan")
    target_hz: float = float("nan")
    note: str = ""
    trace_f: Any = field(default=None, repr=False)
    trace_p: Any = field(default=None, repr=False)

    @property
    def offset_hz(self) -> float:
        return self.freq_hz - self.target_hz


def check_with_sa(sa, center_hz: float, cfg: BeatCheckConfig, name: str = "spectrum analyzer") -> BeatResult:
    sa.configure(center_hz=center_hz, span_hz=cfg.span_hz, rbw_hz=cfg.rbw_hz, vbw_hz=cfg.rbw_hz)
    f, p = sa.sweep_and_fetch()
    i = int(np.argmax(p))
    return BeatResult(found=bool(p[i] >= cfg.min_dbm), source=name, freq_hz=float(f[i]),
                      level_dbm=float(p[i]), target_hz=center_hz, trace_f=f, trace_p=p)


def check_with_scope(scope, center_hz: float, cfg: BeatCheckConfig, name: str = "scope FFT") -> BeatResult:
    t, v = scope.capture(cfg.scope_channel)             # any "scope" capability add-on
    dt = float(t[1] - t[0])
    lo, hi = center_hz - cfg.span_hz / 2, center_hz + cfg.span_hz / 2
    x = (v - v.mean()) * np.hanning(len(v))
    s = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(v), dt)
    # dBm into 50 Ω, approximate (Hann coherent gain 0.5)
    vpk = 2 * np.sqrt(s) / (len(v) * 0.5)
    p = 10 * np.log10(np.maximum((vpk / np.sqrt(2)) ** 2 / 50 / 1e-3, 1e-20))
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return BeatResult(False, name, target_hz=center_hz,
                          note="span is above the scope's Nyquist at this timebase")
    i = np.where(m)[0][int(np.argmax(p[m]))]
    fpk = peak_frequency_fft(v, dt, lo, hi)
    return BeatResult(found=bool(p[i] >= cfg.min_dbm), source=name, freq_hz=fpk,
                      level_dbm=float(p[i]), target_hz=center_hz, trace_f=f[m], trace_p=p[m])


def verify_beat(opl, sa=None, scope=None, cfg: Optional[BeatCheckConfig] = None,
                sa_name: str = "spectrum analyzer", scope_name: str = "scope FFT") -> BeatResult:
    """Counter first; if it shows nothing, ask the analyzer (or scope)."""
    cfg = cfg or BeatCheckConfig()
    target = (opl.get_target_beatnote() or 0.0) * 1e6
    center = cfg.center_hz or target
    if opl.has_beat():
        b = opl.read_beatnote() * 1e6
        return BeatResult(True, "OPL counter", freq_hz=b, target_hz=target)
    if cfg.source == "sa" and sa is not None:
        return check_with_sa(sa, center, cfg, sa_name)
    if cfg.source == "scope" and scope is not None:
        return check_with_scope(scope, center, cfg, scope_name)
    if sa is not None:
        return check_with_sa(sa, center, cfg, sa_name)
    if scope is not None:
        return check_with_scope(scope, center, cfg, scope_name)
    return BeatResult(False, "", target_hz=target, note="no analyzer or scope connected")


# ---- scope as a monitor: FWHM and position of the beat -------------------------------------------------
def beat_fwhm(t: np.ndarray, v: np.ndarray, center_hz: float, span_hz: float = 2e6,
              trace: bool = False) -> Dict[str, Any]:
    """FWHM of the beat in a scope record (Hann FFT, half power = −3 dB, linear interpolation).

    Returns peak_hz, fwhm_hz, level_dbv and rbw_hz (the FFT's equivalent noise bandwidth,
    1.5 bins for Hann): a FWHM near rbw_hz means the line is narrower than the record can resolve.
    ``trace=True`` adds f / p_db (the span, dB relative to the peak) for plotting."""
    v = np.asarray(v, dtype=float)
    dt = float(t[1] - t[0])
    n = len(v)
    x = (v - v.mean()) * np.hanning(n)
    pw = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(n, dt)
    df = f[1] - f[0]
    m = np.where((f >= center_hz - span_hz / 2) & (f <= center_hz + span_hz / 2))[0]
    out = {"peak_hz": float("nan"), "fwhm_hz": float("nan"), "level_dbv": float("nan"), "rbw_hz": 1.5 * df}
    if len(m) < 3:
        return out
    k = m[int(np.argmax(pw[m]))]
    half = pw[k] / 2.0
    lo = k
    while lo > m[0] and pw[lo - 1] > half:
        lo -= 1
    hi = k
    while hi < m[-1] and pw[hi + 1] > half:
        hi += 1

    def cross(i_in, i_out):                       # interpolate where the power crosses half
        a, b = pw[i_in], pw[i_out]
        return f[i_in] + (f[i_out] - f[i_in]) * ((a - half) / (a - b) if a != b else 0.5)
    f_lo = cross(lo, lo - 1) if lo > 0 else f[lo]
    f_hi = cross(hi, hi + 1) if hi + 1 < len(f) else f[hi]
    out["fwhm_hz"] = float(max(f_hi - f_lo, df))
    out["peak_hz"] = float(peak_frequency_fft(v, dt, center_hz - span_hz / 2, center_hz + span_hz / 2))
    vpk = 2 * np.sqrt(pw[k]) / (n * 0.5)
    out["level_dbv"] = float(20 * np.log10(max(vpk / np.sqrt(2), 1e-12)))
    if trace:
        out["f"] = f[m]
        out["p_db"] = 10 * np.log10(np.maximum(pw[m] / pw[k], 1e-20))
    return out


def measure_beat(scope, channel: int, center_hz: float, span_hz: float = 2e6,
                 trace: bool = False) -> Dict[str, Any]:
    """One scope capture → beat FWHM / peak (the scope only watches; nothing is changed)."""
    t, v = scope.capture(channel)
    return beat_fwhm(t, v, center_hz, span_hz, trace)


# ---- the same measurement with the HP 8563E spectrum analyzer (in place of the scope) --------------------
def spectrum_fwhm(f, p_dbm, center_hz: float, span_hz: float, rbw_hz: Optional[float] = None,
                  trace: bool = False) -> Dict[str, Any]:
    """Beat peak and −3 dB width from an analyzer trace (dBm). The width can't be narrower than the RBW:
    a FWHM ≈ rbw_hz means the line is narrower than the analyzer resolves."""
    f = np.asarray(f, dtype=float)
    p = np.asarray(p_dbm, dtype=float)
    m = np.where((f >= center_hz - span_hz / 2) & (f <= center_hz + span_hz / 2))[0]
    out: Dict[str, Any] = {"peak_hz": float("nan"), "fwhm_hz": float("nan"), "level_dbm": float("nan"),
                           "level_dbv": float("nan"), "rbw_hz": rbw_hz or float("nan")}
    if len(m) < 3:
        return out
    k = m[int(np.argmax(p[m]))]
    half = p[k] - 3.0103
    lo = k
    while lo > m[0] and p[lo - 1] > half:
        lo -= 1
    hi = k
    while hi < m[-1] and p[hi + 1] > half:
        hi += 1

    def cross(i_in, i_out):
        a, b = p[i_in], p[i_out]
        return f[i_in] + (f[i_out] - f[i_in]) * ((a - half) / (a - b) if a != b else 0.5)
    df = f[1] - f[0]
    f_lo = cross(lo, lo - 1) if lo > 0 else f[lo]
    f_hi = cross(hi, hi + 1) if hi + 1 < len(f) else f[hi]
    out["fwhm_hz"] = float(max(f_hi - f_lo, df))
    if 0 < k < len(p) - 1:                                  # parabolic peak interpolation (in dB)
        a, b, c = p[k - 1], p[k], p[k + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        out["peak_hz"] = float(f[k] + d * df)
    else:
        out["peak_hz"] = float(f[k])
    out["level_dbm"] = float(p[k])
    out["level_dbv"] = float(p[k] - 13.01)                 # 50 Ω: dBV = dBm − 13.01, for the shared display
    if trace:
        out["f"] = f[m]
        out["p_db"] = p[m] - p[k]
    return out


def measure_beat_sa(sa, center_hz: float, span_hz: float = 2e6, trace: bool = False) -> Dict[str, Any]:
    """One analyzer sweep around the target → beat FWHM / peak. Centre and span are set only when they differ
    (nothing else on the analyzer is changed); the RBW is the analyzer's own (coupled unless you set it)."""
    s = sa.settings()
    if s.get("center_hz") is None or abs(s["center_hz"] - center_hz) > 1:
        sa.set_center_hz(center_hz)
    if s.get("span_hz") is None or abs(s["span_hz"] - span_hz) > 1:
        sa.set_span_hz(span_hz)
    f, p = sa.sweep_and_fetch()
    rbw = sa.qf("RB?")
    r = spectrum_fwhm(f, p, center_hz, span_hz, rbw, trace)
    r["instrument"] = "sa"
    return r


def measure_beat_any(dev, center_hz: float, span_hz: float, channel: int = 2, trace: bool = False):
    """Scope (time record → FFT) or spectrum analyzer: same result fields either way."""
    if hasattr(dev, "sweep_and_fetch"):
        return measure_beat_sa(dev, center_hz, span_hz, trace)
    return measure_beat(dev, channel, center_hz, span_hz, trace)
