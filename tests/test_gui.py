"""Headless GUI smoke test: build, connect to the simulator, restart, check state came back."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from laserlock import discovery  # noqa: E402
from laserlock.settings import Settings  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from laserlock.gui import theme
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    a.setStyleSheet(theme.QSS)
    return a


def _pump(app, sec):
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(int(sec * 1000), loop.quit)
    loop.exec()


def test_gui_builds_connects_and_restores(app, world, tmp_path, monkeypatch):
    from laserlock.gui import widgets as W
    from laserlock.gui.main_window import MainWindow
    monkeypatch.setattr(W, "confirm", lambda *a, **k: True)
    from laserlock_addons.laser_lock.pages import process as _proc
    asked = []
    monkeypatch.setattr(_proc, "_ask_always", lambda *a, **k: asked.append(a[2]) or True)

    path = tmp_path / "settings.json"
    s = Settings(path, autosave_delay=0.05)
    win = MainWindow(s, simulated=True)
    win.show()
    res = discovery.assign_roles(discovery.scan_all(), s.get("roles", {}))
    win.connect_found(res.assignments, res)
    _pump(app, 2.0)
    from laserlock.addonkit import REGISTRY
    assert {"overview", "laserlock", "opl2", "laser"} <= set(win.pages)
    for key in win.pages:
        win.show_page(key)
        _pump(app, 0.2)
    for spec in REGISTRY.windows:
        win.open_window(spec.key)
        _pump(app, 0.3)
    assert not REGISTRY.windows and not win.windows                 # no separate scope window any more
    from laserlock_addons.laser_lock.pages.beat_monitor import BeatMonitor
    lp_mon, opl_mon = win.pages["laserlock"].mon, win.pages["opl2"].mon
    assert isinstance(lp_mon, BeatMonitor) and isinstance(opl_mon, BeatMonitor)
    assert [c.key for c in REGISTRY.chain] == ["comb", "laser"]
    lp = win.pages["laserlock"]
    lp._comb_pill()
    assert "Comb app" in lp.pill_comb.text() or "comb" in lp.pill_comb.text().lower()
    win.show_page("opl2")
    win.pages["opl2"].bc_span.setValue(33e6); win.pages["opl2"].bc_span.editingFinished.emit()
    win.close()
    _pump(app, 0.3)

    s2 = Settings(path)
    assert s2.get("ui.main.page") == "opl2"
    assert s2.get("ui.opl2.beatcheck.span_hz") == 33e6
    assert s2.get("roles.opl2.serial") == "OPL-0002"

    win2 = MainWindow(s2, simulated=True)
    win2.close()


def test_plot_wheel_needs_ctrl_and_exports(app, tmp_path):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from laserlock import datafile
    from laserlock.gui import widgets as W
    p = W.plot(200, "Power (W)", "Frequency (Hz)", title="t")
    p.resize(400, 300)
    p.show()
    p.plot([1e6, 2e6, 3e6], [1e-6, 3e-6, 2e-6], name="a")
    _pump(app, 0.2)
    vb = p.getPlotItem().getViewBox()
    before = vb.viewRange()
    ev = QWheelEvent(QPointF(200, 150), QPointF(200, 150), QPoint(0, 0), QPoint(0, 120), Qt.NoButton,
                     Qt.NoModifier, Qt.NoScrollPhase, False)
    p.wheelEvent(ev)
    assert not ev.isAccepted() and vb.viewRange() == before and vb.autoRangeEnabled()[0]
    assert p.getPlotItem().getAxis("bottom").labelUnits == "Hz"          # SI prefixes come from the unit
    path = p.save_csv(str(tmp_path / "plot.csv"))
    meta = datafile.read_header(path)
    assert meta["plot_curves"] == ["a"] and meta["columns"] == ["Frequency (Hz)", "Power (W)"]
    assert p.save_png(str(tmp_path / "plot.png")) and (tmp_path / "plot.png").stat().st_size > 1000
