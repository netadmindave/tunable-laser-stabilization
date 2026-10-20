"""Who may use the Rigol right now: the Rigol window, or one OPL #2 / Laser lock feature — never both.

* While the Rigol window is open, features can't take the scope (beat check, live beat spectrum,
  lock monitor, scope auto-tune). They show ``BLOCKED_TEXT`` instead.
* While a feature holds the scope, an open Rigol window stays passive (controls disabled) and takes
  the scope back as soon as the feature releases it.

Pure Python (no Qt): listeners are called from whatever thread made the change, so GUI code should
re-emit through a Qt signal.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, List, Optional

BLOCKED_TEXT = "Rigol window is open — close it to use the scope here"

_lock = threading.Lock()
_window = False
_owner: Optional[str] = None
_count = 0
_listeners: List[Callable[[], None]] = []


def _notify():
    for cb in list(_listeners):
        try:
            cb()
        except Exception:
            pass


def subscribe(cb: Callable[[], None]) -> None:
    _listeners.append(cb)


def unsubscribe(cb: Callable[[], None]) -> None:
    if cb in _listeners:
        _listeners.remove(cb)


def set_window_open(on: bool) -> None:
    global _window
    with _lock:
        changed = _window != bool(on)
        _window = bool(on)
    if changed:
        _notify()


def window_open() -> bool:
    return _window


def owner() -> Optional[str]:
    return _owner


def window_has_scope() -> bool:
    """The Rigol window is open and no feature is still holding the scope."""
    return _window and _owner is None


def blocked_reason(name: str = "") -> str:
    """'' when ``name`` could take the scope now, otherwise why not."""
    if _window:
        return BLOCKED_TEXT
    if _owner not in (None, name):
        return f"scope busy: {_owner}"
    return ""


def acquire(name: str, wait_s: float = 0.0) -> bool:
    """Take the scope for a feature. False while the Rigol window is open (or another feature holds it
    longer than ``wait_s``). The same name may acquire again (counted)."""
    global _owner, _count
    end = time.time() + wait_s
    while True:
        with _lock:
            if not _window and _owner in (None, name):
                _owner = name
                _count += 1
                first = _count == 1
                break
        if time.time() >= end:
            return False
        time.sleep(0.1)
    if first:
        _notify()
    return True


def release(name: str) -> None:
    global _owner, _count
    with _lock:
        if _owner != name:
            return
        _count -= 1
        freed = _count <= 0
        if freed:
            _owner, _count = None, 0
    if freed:
        _notify()


def reset() -> None:
    """Tests only."""
    global _window, _owner, _count
    with _lock:
        _window, _owner, _count = False, None, 0
