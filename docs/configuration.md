# Configuration

## Settings file

All settings — saved instruments, window layout, every field you edit — live in one JSON file:

* default: `%LOCALAPPDATA%\laserlock\settings.json`
* override: the `--settings FILE` option, or the `LASERLOCK_SETTINGS` environment variable

The file is written a moment after each change (atomically: a crash can't leave half a file). The application
log, `laserlock.log`, is written next to it and reloaded at start (Devices → Logs…).

## Saved instruments (roles)

Every instrument has a *role* (e.g. `scope`, `opl2`). The Devices dialog assigns instruments to roles and saves
them under `roles` **by serial number**, so a moved USB/COM port is found again (status "moved").

```json
"roles": {
  "scope": {"kind": "rigol_mho5104", "address": "USB0::0x1AB1::0x0450::MHO5C283M0017::INSTR",
            "serial": "MHO5C283M0017", "model": "MHO5104"}
}
```

At start-up the saved instruments are connected directly (no scan). An instrument another bench application has connected is reported as "in use by …" and left alone.

## Shared instrument claims

Tunable Laser Stabilization and Lab Tools Management share instruments (the Rigol, the lasers, the HP 8563E). Connecting one writes a small claim file to `%LOCALAPPDATA%\BenchClaims`; the other application refuses to connect it ("in use by …"), disables its Connect buttons and never probes it while scanning. Claims are released on disconnect and exit; a claim left by a crashed application is ignored.

## Data files

Recordings, sweeps and captures are CSV files with a `#` metadata header (instrument, settings, time). The
default folder is set under Settings; each window's Save button shows the full path in the log.

## Environment variables

| Variable | Effect |
|---|---|
| `LASERLOCK_SETTINGS` | settings file to use |
| `BENCH_CLAIMS_DIR` | folder for the cross-app instrument claims (default `%LOCALAPPDATA%\BenchClaims`) |
| `QT_QPA_PLATFORM=offscreen` | run without a display (tests, servers) |
