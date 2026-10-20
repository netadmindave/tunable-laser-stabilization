"""Laser lock module: lasers, Rigol, beat check, laser lock sequence, scope monitor (simulated bench)."""
import pytest

from laserlock import SafetyError


def _scope_fast(scope):
    scope.set_memory_depth(100000); scope.set_timebase_scale(20e-6)      # 500 MS/s, 2 ms record


def _comb_ok():
    return True, "comb locked (test)"


def test_laser_grid_rounding_and_output(bench):
    las = bench.laser
    las.set_wavelength_nm(1550.123)
    assert abs(las.get_wavelength_nm() - 1550.12) < 1e-6      # HP 8168E 10 pm grid, nearest step
    las.set_wavelength_nm(1550.126)
    assert abs(las.get_wavelength_nm() - 1550.13) < 1e-6      # rounds up when that is closer
    las.output_on()                                           # no confirmation needed any more
    assert las.output_is_on()
    las.output_off()
    with pytest.raises(SafetyError):
        las.set_wavelength_nm(1600.0)                         # range limit still enforced


def test_laser_options_and_power_units(bench):
    las = bench.laser
    las.set_power_w(250e-6)
    p = las.poll()
    assert abs(p["power_w"] - 250e-6) < 1e-9 and abs(p["power_dbm"] - (-6.0206)) < 1e-3
    o = las.read_options()
    assert o["am_source"] in ("0", "1", "2") and 1474 < o["wl_min_nm"] < 1476
    las.write_option("am_freq_hz", 120e3)
    assert las.read_option("am_freq_hz") == 120e3
    las.write_option("wl_ref_set")
    assert abs(las.read_option("wl_ref_nm") - las.get_wavelength_nm()) < 1e-6


def test_comb_tooth():
    from laserlock_addons.laser_lock.comb_tooth import laser_sigma_hz, nearest_tooth
    frep, fceo = 100e6, 20e6
    n = 1_934_020
    nu = n * frep + fceo + 30e6
    t = nearest_tooth(nu, frep, fceo, laser_sigma_hz(nu, 0.1), measured_beat_hz=30e6)
    assert t.n == n and abs(t.offset_hz - 30e6) < 1 and t.side == "above"
    assert 120 <= t.n_uncertainty <= 130                     # ±0.1 nm ≈ ±12.5 GHz ≈ ±125 teeth
    assert abs(t.laser_hz_if_above - nu) < 1


def test_rigol_generic_capture_and_nyquist_plan(bench):
    from laserlock_addons.laser_lock import RigolMHO5104
    t, v = bench.scope.capture(1)
    assert len(t) == len(v) > 100
    assert RigolMHO5104.plan_nyquist(25e6, 1_000_000)["sample_rate"] >= 50e6


def test_beat_check_finds_offset_beat_with_the_scope(bench):
    from laserlock_addons.laser_lock import BeatCheckConfig, verify_beat
    bench.laser.output_on(confirm=True)
    _scope_fast(bench.scope)
    r = verify_beat(bench.opl2, scope=bench.scope, cfg=BeatCheckConfig(source="scope", scope_channel=2), scope_name="Rigol FFT")
    assert r.found and r.source == "Rigol FFT" and abs(r.offset_hz - 1.8e6) < 0.2e6, r
    bench.laser.output_off()


def test_laser_lock_sequence_needs_the_comb(bench):
    from laserlock_addons.laser_lock import LaserLockParams, LaserLockSequence
    seq = LaserLockSequence(bench.devices, LaserLockParams(dwell_s=0.5, poll_s=0.1, servo_wait_s=0.2),
                            comb_status=lambda: (False, "comb: f_rep open"))
    assert not seq.run()
    assert seq.steps["comb"].status == "fail"
    assert not bench.laser.poll()["output_on"]                # nothing was switched on


def _lock_run(world, bench, **kw):
    """Target 51.8 MHz as given (where the sim laser beat sits at 1550.100 nm); the OPL #2 counter is blind."""
    from laserlock_addons.laser_lock import LaserLockParams, LaserLockSequence
    asked = []
    _scope_fast(bench.scope)
    world.opl2.counter_blind = True
    bench.opl2.set_target_beatnote(51.8)
    p = dict(wavelength_nm=1550.1, dwell_s=2.0, poll_s=0.1, servo_wait_s=0.2, scope_every_s=0.3,
             beat_still_s=0.5, beat_every_s=0.1, scope_span_hz=2e6)          # short gate for tests
    p.update(kw)
    seq = LaserLockSequence(dict(bench.devices), LaserLockParams(**p),
                            ask=lambda q, rows=None: asked.append(q) or True, comb_status=_comb_ok)
    ok = seq.run()
    return ok, seq, asked


def test_laser_lock_without_counter_beat_scope_monitors(world, bench):
    """Comb → laser → limits → servo → monitor: no counter beat, no retarget, the scope reports the FWHM."""
    from laserlock_addons.laser_lock import scope_owner
    scope_owner.reset()
    ok, seq, asked = _lock_run(world, bench)
    assert ok, [(k, s.status, s.detail) for k, s in seq.steps.items()]
    assert seq.steps["beat"].status == "done" and not any("target" in q.lower() for q in asked)   # no retarget
    assert bench.opl2.read_beatnote() < 1 and world.opl2.locked          # locked with a blind counter
    assert "FWHM" in seq.steps["monitor"].detail and scope_owner.owner() is None
    assert abs(bench.opl2.get_target_beatnote() - 51.8) < 1e-6           # target untouched
    bench.opl2.set_servo(False)
    bench.laser.output_off()


def test_beat_fwhm_on_a_synthetic_line():
    import numpy as np
    from laserlock_addons.laser_lock import beat_fwhm
    fs, n = 500e6, 200_000
    t = np.arange(n) / fs
    r = beat_fwhm(t, 0.1 * np.sin(2 * np.pi * 50.123e6 * t), 50e6, 2e6)
    df = fs / n
    assert abs(r["peak_hz"] - 50.123e6) < df and r["rbw_hz"] == 1.5 * df
    assert df <= r["fwhm_hz"] < 3 * df                                    # a pure tone: about one Hann bin wide


def test_autotune_with_scope_starts_from_existing_settings(world, bench):
    from laserlock_addons.laser_lock import scope_owner
    from laserlock_addons.laser_lock.autotune import AutoTuner, TuneConfig
    scope_owner.reset()
    ok, seq, _ = _lock_run(world, bench, dwell_s=0.3)
    assert ok
    g0 = bench.opl2.get_pll_gain()
    tu = AutoTuner(bench.opl2, TuneConfig(metric="fwhm_move_scope", gains_db=[-50.0], int_corners_hz=[100.0],
                                          strategy="grid", dwell_s=0.0, averages=3, scope_channel=2),
                   scope=bench.scope)
    best = tu.run()
    assert len(tu.trials) == 2 and tu.trials[0].gain_db == g0             # trial 1 = the existing settings
    x = tu.trials[0].extra
    assert {"phase_rad", "fwhm_hz", "move_hz"} <= set(x) and x["fwhm_hz"] > 0 and best is not None
    assert abs(tu.trials[0].score - 2.0) < 1e-9                           # combined score is relative to the start
    bench.opl2.set_servo(False)
    bench.laser.output_off()


def test_comb_status_file(tmp_path, settings):
    import json, time
    from laserlock_addons.laser_lock import comb_link
    path = tmp_path / "comb_status.json"
    settings.set("ui.laser.comb_status_path", str(path))
    assert comb_link.verdict(comb_link.read_status(settings))[1] == "idle"          # comb app not running
    st = {"t": time.time(), "connected": {"opl1": True, "fpga": True, "ffc": True},
          "ffc": {"mode_locked": True}, "opl1": {"frep_locked": True},
          "fpga": {"ceo_locked": True, "ceo_ref_hz": 21.4e6, "ceo_phase_rad": 0.4}, "comb_locked": True}
    path.write_text(json.dumps(st))
    ok, note = comb_link.comb_locked(settings)
    assert ok and "0.40 rad" in note and comb_link.fceo_hz(settings) == 21.4e6
    st.update(comb_locked=False, opl1={"frep_locked": False}, t=time.time())
    path.write_text(json.dumps(st))
    ok, note = comb_link.comb_locked(settings)
    assert not ok and "f_rep open" in note
    st.update(t=time.time() - 60, comb_locked=True)
    path.write_text(json.dumps(st))
    assert comb_link.verdict(comb_link.read_status(settings))[1] == "warn"          # stale
def test_rigol_open_clears_and_retries():
    from laserlock_addons.laser_lock import RigolMHO5104

    class Inst:
        timeout, resource_name = 5000, "USB0::X::INSTR"
        def __init__(self): self.log, self.fail = [], 1
        def clear(self): self.log.append("clear")
        def write(self, c):
            if self.fail:
                self.fail -= 1
                raise OSError("VI_ERROR_NCIC")
            self.log.append(c)
    i = Inst()
    RigolMHO5104("USB0::X::INSTR", inst=i)
    assert i.log == ["clear", "clear", "*CLS"]


def test_railed_servo_is_broken_and_relocked(world, bench):
    """Servo already on and railed (integrator wound up): the servo step breaks the lock, then it locks."""
    bench.laser.set_wavelength_nm(1550.1)
    bench.laser.output_on()
    bench.opl2.set_target_beatnote(50.0)          # beat 1.8 MHz away: servo on rails
    bench.opl2.set_servo(True)
    bench.opl2.set_target_beatnote(51.8)          # now in range, but a railed servo won't capture by itself
    assert not world.opl2.locked
    ok, seq, _ = _lock_run(world, bench, dwell_s=0.5)
    assert ok and world.opl2.locked and seq.steps["beat"].status == "done", seq.steps["beat"].detail   # broken
    # first (servo off), the beat checked, then locked
    bench.opl2.set_servo(False)
    bench.laser.output_off()


def test_rail_that_wont_clear_gives_up_with_servo_off(world, bench, monkeypatch):
    ok, seq, _ = _lock_run(world, bench, dwell_s=0.5, rail_relocks=1, break_wait_s=0.1)
    assert ok
    bench.opl2.set_servo(False)
    from laserlock_addons.laser_lock import LaserLockParams, LaserLockSequence
    bench.opl2.set_target_beatnote(50.0)          # can never lock here
    seq = LaserLockSequence(dict(bench.devices), LaserLockParams(dwell_s=0.5, poll_s=0.1, servo_wait_s=0.2,
                                                                 rail_relocks=1, break_wait_s=0.1),
                            comb_status=_comb_ok)
    assert not seq.run()
    d = seq.steps["monitor"].detail
    assert "after 1 relock" in d and "servo left OFF" in d and not bench.opl2.servo_on(), d
    bench.laser.output_off()


def test_laser_setpoint_ranges(world, bench):
    from laserlock_addons.laser_lock import laser_setpoints as sp
    assert sp.check(1550.1, 500e-6) == {}
    ch = sp.check(1549.8, 100e-6)
    assert ch["wavelength_nm"][1] == 1550.0 and ch["power_w"][1] == 1e-3
    assert set(sp.check(1550.3, 1.2e-3)) == {"wavelength_nm", "power_w"}
    bench.laser.set_wavelength_nm(1560.0)
    bench.laser.set_power_w(50e-6)
    sp.apply(bench.laser, sp.check(bench.laser.get_wavelength_nm(), bench.laser.get_power_w()))
    assert abs(bench.laser.get_wavelength_nm() - 1550.0) < 1e-6 and abs(bench.laser.get_power_w() - 1e-3) < 1e-9


def test_instrument_held_by_lab_tools_is_refused(world):
    """Claims are shared with Lab Tools: a live claim from another process blocks opening and probing."""
    import json, os, subprocess, sys
    from laserlock import discovery
    from laserlock.core import claims
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    addr = "GPIB2::2::INSTR"
    try:
        claims._path(addr).write_text(json.dumps({"app": "Lab Tools", "pid": other.pid, "address": addr}))
        try:
            discovery.open_found(discovery.Found("hp8168", addr, "GPIB"))
            assert False, "should have been refused"
        except claims.InUse as e:
            assert e.app == "Lab Tools"
        assert all(f.address != addr for f in discovery.scan_all().found)
    finally:
        other.kill(); other.wait()
    assert claims.holder(addr) is None


def test_spectrum_fwhm_on_a_synthetic_line():
    import numpy as np
    from laserlock_addons.laser_lock.beat_check import spectrum_fwhm
    f = np.linspace(49e6, 51e6, 601)
    p = -20 - 10 * np.log10(1 + ((f - 50.1e6) / 50e3) ** 2)          # Lorentzian, FWHM 100 kHz
    r = spectrum_fwhm(f, p, 50e6, 2e6, rbw_hz=10e3)
    assert abs(r["peak_hz"] - 50.1e6) < 5e3 and abs(r["fwhm_hz"] - 100e3) < 8e3 and r["level_dbm"] > -20.1


def test_lock_with_the_spectrum_analyzer_as_beat_instrument(world, bench):
    """Same lock, monitored by the HP 8563E instead of the Rigol."""
    from laserlock_addons.laser_lock import scope_owner
    scope_owner.reset()
    ok, seq, _ = _lock_run(world, bench, beat_role="sa", scope_every_s=0.5)
    assert ok, [(k, s.status, s.detail) for k, s in seq.steps.items()]
    d = seq.steps["monitor"].detail
    assert "spectrum analyzer FWHM" in d, d
    bench.opl2.set_servo(False)
    bench.laser.output_off()


def test_autotune_fwhm_with_the_spectrum_analyzer(world, bench):
    from laserlock_addons.laser_lock import scope_owner
    from laserlock_addons.laser_lock.autotune import AutoTuner, TuneConfig
    scope_owner.reset()
    ok, seq, _ = _lock_run(world, bench, dwell_s=0.3)
    assert ok
    tu = AutoTuner(bench.opl2, TuneConfig(metric="fwhm_scope", gains_db=[-50.0], int_corners_hz=[100.0],
                                          strategy="grid", dwell_s=0.0, averages=3), scope=bench.sa)
    best = tu.run()
    assert best is not None and len(tu.trials) == 2 and tu.trials[0].extra["fwhm_hz"] > 0
    bench.opl2.set_servo(False)
    bench.laser.output_off()


def test_beat_gate_waits_until_near_and_steady(world, bench):
    """Target 50 MHz while the beat sits at 51.8: within 10 MHz → the gate passes after the still time;
    a 10 kHz 'near' window can't be met → it times out and the servo stays off."""
    from laserlock_addons.laser_lock import scope_owner
    scope_owner.reset()
    ok, seq, _ = _lock_run(world, bench, beat_still_s=1.0, scope_span_hz=20e6)
    assert ok and seq.steps["beat"].status == "done", seq.steps["beat"].detail
    bench.opl2.set_servo(False)
    ok, seq, _ = _lock_run(world, bench, beat_near_hz=10.0, beat_timeout_s=1.5)
    assert not ok and seq.steps["beat"].status == "fail" and not bench.opl2.servo_on()
    bench.laser.output_off()
