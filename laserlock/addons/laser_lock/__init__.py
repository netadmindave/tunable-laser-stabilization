"""Laser lock module — tunable laser, SLICE-OPL #2 (Brimrose AOM), Rigol MHO5104 (beat monitor), Laser lock page.

Scripting::

    import laserlock
    ll = laserlock.addon("laser_lock")
    with ll.HP8168.find() as laser:
        laser.set_wavelength_nm(1550.1)
"""
from __future__ import annotations

import time

from .sliceopl import SliceOPL
from .hp8168 import HP8168
from .sws17101 import SWS17101
from .rigol_mho5104 import RigolMHO5104
from .beat_check import BeatCheckConfig, beat_fwhm, measure_beat, verify_beat
from .laser_sequence import LaserLockParams, LaserLockSequence

SECTION = "LASER LOCK"


def _classify(idn: str):
    u = idn.upper()
    if "8168" in u:
        return "hp8168"
    if any(w in u for w in ("SWS1", "JDS_UNIPHASE", "JDS UNIPHASE", "TUNICS")):
        return "sws17101"
    if "MHO5" in u or ("RIGOL" in u and "MHO" in u):
        return "rigol_mho5104"
    return None


_SWS_WORDS = ("SWS", "JDS", "UNIPHASE", "TUNICS", "PHOTONETICS")


def _probe_sws(inst, res, bus, opts):
    """The SWS17101 answers *IDN? only through its status byte (MAV): ask, wait for the data-ready bit
    (up to 2 s, as in the notebook), then do one bounded read and strip the 'X=' prefix."""
    from laserlock.discovery import Found
    old = getattr(inst, "timeout", None)
    try:
        inst.timeout = 2000
        inst.read_termination = "\n"
        inst.write_termination = "\n"
    except Exception:
        pass
    try:
        inst.write("*IDN?")
        time.sleep(0.3)
        t_end = time.time() + 2.0
        while time.time() < t_end:
            try:
                if inst.read_stb() & 0x01:
                    break
            except Exception:
                break
            time.sleep(0.05)
        raw = inst.read().strip()
    finally:
        if old is not None:
            try:
                inst.timeout = old
            except Exception:
                pass
    idn = raw.split("=", 1)[1] if "=" in raw else raw
    if not any(w in idn.upper() for w in _SWS_WORDS):
        return None
    p = [x.strip() for x in idn.split(",")]
    return Found("sws17101", res, bus, model=p[1] if len(p) > 1 else "SWS17101", serial=p[2] if len(p) > 2 else "",
                 how="*IDN? (status-byte read)", raw=idn)


# ---- SLICE-OPL #2 discovery (USB serial, *IDN? with CR) ------------------------------------------
def _vescent_port(info) -> bool:
    """Any USB-serial port except FTDI. (A port already held by the Vescent Comb app is busy and skipped.)"""
    return info.usb_family != "ftdi"


def _probe_opl(info, opts):
    from laserlock.discovery import Found, split_idn, with_serial
    from laserlock.core.serialio import SerialLine
    timeout = max(opts.serial_timeout, 1.5)

    def ask(ser):
        time.sleep(0.3)
        ser.reset_input_buffer()
        return SerialLine(ser=ser, eol="\r", quiet=0.05).query("*IDN?", timeout=timeout)

    reply = with_serial(info.device, 115200, timeout, ask) or ""
    if "OPL" not in reply.upper():
        return None
    p = split_idn(reply)
    return Found("sliceopl", info.device, "USB serial", model=p[1] if len(p) > 1 else "SLICE-OPL",
                 serial=p[2] if len(p) > 2 else info.serial_number,
                 firmware=" / ".join(p[3:5]) if len(p) > 3 else "", how="*IDN? (CR)", raw=reply,
                 extra={"usb_serial": info.serial_number})


def _pill_laser(d, settings):
    """Locked = servo on and PLL output off its rails (the OPL counter may never see the beat)."""
    if not d.get("servo_on"):
        return "servo off", "idle"
    lo, hi, out = d.get("pll_min"), d.get("pll_max"), d.get("pll_out_v")
    if not all(isinstance(x, float) for x in (lo, hi, out)) or hi <= lo:
        return "servo on", "warn"
    m = 0.05 * (hi - lo)
    return ("locked", "ok") if lo + m < out < hi - m else ("PLL on the rail", "warn")


def _scope_summary(d):
    return str(d.get("trigger_status") or "")


# ---- HP 8563E spectrum analyzer: optional beat instrument in place of the Rigol ---------------------
def _sa_classify(idn: str):
    return "hp8563e" if "8563" in idn else None


def _sa_probe(inst, res, bus, opts):
    """The 8563E doesn't answer *IDN?; it answers ID? and SER?."""
    from laserlock.discovery import Found
    ident = inst.query("ID?").strip()
    if "85" not in ident:
        return None
    serial = ""
    try:
        serial = inst.query("SER?").strip()
    except Exception:
        try:
            inst.clear()
        except Exception:
            pass
    return Found("hp8563e", res, bus, model=ident, serial=serial, how="*IDN? timeout → ID?, SER?", raw=ident)


def _sa_summary(d):
    from laserlock.core.units import eng
    if isinstance(d.get("center_hz"), float):
        return f"CF {eng(d['center_hz'], 'Hz')} · SP {eng(d.get('span_hz') or 0, 'Hz')}"
    return ""


def register(api):
    api.add_device("sliceopl", SliceOPL, "Vescent SLICE-OPL")
    api.add_serial_probe("Vescent SLICE-OPL *IDN?", _vescent_port, _probe_opl, priority=60)
    api.add_opener("sliceopl", api.serial_opener(SliceOPL, 115200, 1.0))
    api.add_device("hp8168", HP8168, "HP 8168D/E tunable laser")
    api.add_device("sws17101", SWS17101, "JDSU SWS17101 tunable laser")
    api.add_device("rigol_mho5104", RigolMHO5104, "Rigol MHO5104 oscilloscope")

    api.add_role("opl2", "OPL #2 · laser → Brimrose", ["sliceopl"], capabilities=("opl",), order=20)
    api.add_role("laser", "Tunable laser", ["hp8168", "sws17101"], capabilities=("tunable_laser",),
                 poll_s=2.0, order=21)
    api.add_role("scope", "Oscilloscope · Rigol MHO5104", ["rigol_mho5104"], capabilities=("scope",),
                 poll_s=2.0, bench_row=True, order=30)

    api.add_visa_classifier(_classify)
    api.add_visa_probe("SWS17101 status-byte read", _probe_sws, priority=60)
    api.add_safe_standby("laser", "tunable laser output OFF")

    api.add_page("laserlock", "Laser lock", "pages.process:LaserLockPage", section=SECTION, order=20)
    api.add_chain_pill("comb", "Comb (Vescent Comb app)", "opl2", _pill_comb, order=10)
    api.add_page("opl2", "SLICE-OPL #2 · laser", "pages.opl2:OPL2Page", role="opl2", section=SECTION, order=21)
    api.add_page("laser", "Tunable laser", "pages.laser:LaserPage", role="laser", section=SECTION, order=22)
    # no separate scope window: the beat monitor sits on the Laser lock and OPL #2 pages

    api.add_overview_panel("opl2", "overview:OPL2Card", order=20)
    api.add_overview_panel("laser", "overview:LaserCard", order=21)
    api.add_chain_pill("laser", "Laser → comb · OPL #2", "opl2", _pill_laser, order=20)
    api.add_summary("scope", _scope_summary)

    api.add_reference("scope", "rear 10 MHz REF IN", "switch", status=lambda d: d.get("ext_ref"), option="ext_ref",
                      note=":SYSTem:RCLock")

    from laserlock.core.units import eng

    def _opl2_ref(d):
        r = d.get("reference")
        return None if not isinstance(r, (int, float)) else abs(r - 10.0) < 0.01
    api.add_reference("opl2", "REF IN (GPS 10 MHz)", "always", status=_opl2_ref,
                      detail=lambda d: "READREF? " + (eng(d["reference"] * 1e6, "Hz", 9)
                                                      if isinstance(d.get("reference"), (int, float)) else "—"),
                      note="reference measured by the OPL")
    api.on_connect("hp8168", _apply_grid)
    from .hp8563e import HP8563E
    api.add_device("hp8563e", HP8563E, "HP 8563E")
    api.add_role("sa", "Spectrum analyzer · HP 8563E (beat instrument)", ["hp8563e"], capabilities=("spectrum",),
                 poll_s=3.0, bench_row=True, order=34)
    api.add_visa_classifier(_sa_classify)
    api.add_visa_probe("HP 85xx ID?/SER?", _sa_probe, priority=40)
    api.add_summary("sa", _sa_summary)
    api.add_reference("sa", "rear J9 10 MHz REF IN", "switch", status=lambda d: d.get("ext_ref"), option="ext_ref",
                      note="FREF EXT/INT")
    api.add_sim("sim:install")


def _pill_comb(d, settings):
    from .comb_link import read_status, verdict
    return verdict(read_status(settings))


def _apply_grid(dev, settings):
    """Tuning step chosen on the Laser page (8168E: 10 pm by default, 1 pm per the manual)."""
    key = "hp8168e" if getattr(dev, "model", "") == "8168E" else "hp8168d"
    g = settings.get(f"ui.laser.grid_nm.{key}") if settings is not None else None
    if g:
        dev.grid_nm = float(g)
