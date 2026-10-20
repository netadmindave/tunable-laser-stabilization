# User guide

## Laser lock page

**Tunable laser** — wavelength and power fields follow the laser (they stop following while you type). When the
laser connects, and again when you lock, you're asked to bring it into range if it's outside 1549.9–1550.2 nm
(→ 1550.000 nm) or 200 µW–1 mW (→ 1 mW).

**OPL #2** — target, servo, PLL output with its limits; "laser locked" means servo on and PLL output off its
rails (the OPL counter is information only).

**Comb** — the comb state from Vescent FFC-100 GPS locking (`comb_status.json`) and the comb tooth near the laser.

**Beat monitor** — choose the **beat instrument** (Rigol MHO5104 or HP 8563E), the scope channel and the span
around the OPL target (default 70 MHz). Shows the spectrum (linear power), peak − target, FWHM (with the RBW),
movement over the last 10 peaks, and level. It captures only while visible with "Live" ticked; it never
changes the instrument except, on the analyzer, centre and span.

**Lock steps** — the sequence, run with **Lock laser**:

1. **Comb** locked (untick "Require the comb" to skip).
2. **Laser** on at the set wavelength (asks first).
3. **Limits** — PLL limits inside the Brimrose window (7–12 V).
4. **Beat check** — the free-running beat must be **within** 10 MHz of the target and **moving less than** 10 MHz
   (peak to peak) **for** 30 s, or the step gives up after 600 s and the servo stays off. All four values are
   editable. Skipped if already locked; a railed lock is broken first.
5. **Servo** on at the OPL target as set (the target is never moved).
6. **Monitor** — for the watch time: servo stays on and PLL output stays off its rails (two railed samples →
   break and relock, up to 2 times, then servo OFF); the beat instrument reports FWHM, offset and movement
   ("Max FWHM" > 0 makes FWHM a pass condition).

**Relock watchdog** and **rail guard** — relock after a lasting loss, or when the PLL output rails with the
servo on; both share the hourly limit.

**Trends** — OPL beat error, and the beat instrument's FWHM and peak offset during locks.

## OPL #2 page

Target, dividers, servo filter, limits, sweep; **Beat monitor** tab (same panel as the Laser lock page); **Beat
check** tab (counter, then the beat instrument; only looks). **Auto-tune** tries filter settings starting from
the current ones and scores each trial: integrated phase (scope only), beat FWHM, movement, FWHM and movement
together, noise pedestal or servo bump (analyzer). Trial table shows phase, FWHM and movement for every trial.

## Devices dialog

Sections for serial, GPIB/VISA and Bluetooth instruments: roles on the left, scan results on the right.
Instruments another application holds show "in use by …" and can't be connected.

## 10 MHz references

Overview → references: tick external 10 MHz for the Rigol (`:SYSTem:RCLock`) or the HP 8563E (`FREF`). Your choice
is remembered and applied each time the instrument connects.
