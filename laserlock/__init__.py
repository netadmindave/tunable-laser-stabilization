"""laserlock — locking the tunable laser to the comb: SLICE-OPL #2 (Brimrose AOM), the tunable
laser (HP 8168D/E or JDSU SWS17101) and the Rigol MHO5104.

A stand-alone application: the laser module is built in and always loaded (no add-on manager).
The comb itself is run by the Vescent Comb app; this app only reads its status file.
"""

__version__ = "0.1.0"

from .core.base import Device, DeviceError, Identity, SafetyError  # noqa: F401
from .settings import Settings, default_settings_path              # noqa: F401
from . import datafile                                               # noqa: F401  (CSV with bench-state header)


def load_addons(settings=None, **kw):
    """Load the add-ons enabled in the settings file (installing requirements on first use)."""
    from .addonkit import load_enabled
    return load_enabled(settings if settings is not None else Settings(), **kw)


def addon(addon_id: str, settings=None):
    """Load one add-on (and its dependencies), even if it is unchecked, and return its package."""
    from .addonkit import load
    return load(addon_id, settings if settings is not None else Settings())
