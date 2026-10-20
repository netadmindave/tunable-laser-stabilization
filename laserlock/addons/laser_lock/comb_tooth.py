"""Which comb tooth is the laser next to?  ν_n = n·f_rep + f_ceo.

The tooth number comes from the laser's own frequency readback, so its certainty is limited by
the laser's absolute accuracy (HP 8168E: ±0.1 nm ≈ ±12.5 GHz ≈ ±125 teeth at 100 MHz). Give a
wavemeter reading (``known_nu_hz``) to pin it down. The beat frequency itself (|ν − ν_n|) is
exact once the OPL #2 counter reads it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

C = 299_792_458.0


@dataclass
class Tooth:
    n: int                       # tooth index
    nu_n_hz: float               # tooth frequency
    lambda_n_nm: float
    offset_hz: float             # laser − tooth (signed), |offset| ≤ f_rep/2
    expected_beat_hz: float      # |offset| — what the beat counter should read if the estimate were exact
    n_uncertainty: Optional[int]  # ± teeth from the frequency uncertainty (None = unknown)
    side: str                    # "above" / "below" the tooth
    measured_beat_hz: Optional[float] = None
    laser_hz_if_above: Optional[float] = None
    laser_hz_if_below: Optional[float] = None


def nearest_tooth(nu_hz: float, frep_hz: float, fceo_hz: float = 0.0, sigma_nu_hz: Optional[float] = None,
                  measured_beat_hz: Optional[float] = None) -> Tooth:
    if not (frep_hz and frep_hz > 0):
        raise ValueError("f_rep must be > 0")
    n = int(round((nu_hz - fceo_hz) / frep_hz))
    nu_n = n * frep_hz + fceo_hz
    off = nu_hz - nu_n
    unc = None if sigma_nu_hz is None else int(math.ceil(abs(sigma_nu_hz) / frep_hz))
    t = Tooth(n, nu_n, C / nu_n * 1e9, off, abs(off), unc, "above" if off >= 0 else "below")
    if measured_beat_hz is not None and measured_beat_hz > 0:
        t.measured_beat_hz = measured_beat_hz
        t.laser_hz_if_above = nu_n + measured_beat_hz
        t.laser_hz_if_below = nu_n - measured_beat_hz
    return t


def laser_sigma_hz(nu_hz: float, accuracy_nm: float) -> float:
    """Frequency uncertainty of a wavelength readback with ±``accuracy_nm`` absolute accuracy."""
    lam = C / nu_hz
    return C * accuracy_nm * 1e-9 / lam ** 2
