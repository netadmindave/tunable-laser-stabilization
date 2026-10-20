# Python API guide

Full list of modules, classes and methods: [api-reference.md](api-reference.md).

## Imports

```python
from laserlock import discovery                    # find, open and connect instruments
from laserlock.settings import Settings
from laserlock.addonkit import load
ll = load("laser_lock")                            # drivers, lock sequence, beat measurements
from laserlock_addons.laser_lock.laser_sequence import LaserLockSequence, LaserLockParams
from laserlock_addons.laser_lock.beat_check import measure_beat, measure_beat_sa, beat_fwhm, spectrum_fwhm
from laserlock_addons.laser_lock.comb_link import comb_locked, read_status
from laserlock_addons.laser_lock.autotune import AutoTuner, TuneConfig
from laserlock_addons.laser_lock import laser_setpoints
from laserlock import sim
```

## Connect and read

```python
with discovery.connect_all() as bench:
    opl2, laser, scope = bench.devices["opl2"], bench.devices["laser"], bench.devices.get("scope")
    print(opl2.poll()["pll_out_v"], laser.get_wavelength_nm())
```

## Run the lock

```python
p = LaserLockParams(wavelength_nm=1550.0, beat_role="scope", beat_near_hz=10e6, beat_still_hz=10e6,
                    beat_still_s=30, scope_span_hz=70e6)
seq = LaserLockSequence(bench.devices, p, on_step=lambda s: print(s.id, s.status, s.detail),
                        ask=lambda q, rows=None: True)
ok = seq.run()
```

## Measure the beat

```python
r = measure_beat(scope, 2, center_hz=50e6, span_hz=70e6)          # scope: FFT of CH2
r = measure_beat_sa(bench.devices["sa"], 50e6, 70e6)               # HP 8563E
print(r["peak_hz"], r["fwhm_hz"], r["rbw_hz"])
```

## Auto-tune

```python
tu = AutoTuner(opl2, TuneConfig(metric="fwhm_scope", gains_db=[-55, -50, -45]), scope=scope)
best = tu.run()
```
