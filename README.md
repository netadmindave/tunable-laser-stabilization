# Tunable Laser Stabilization

Locks a tunable laser (**HP 8168D/E** or **JDSU SWS17101**) to a GPS-locked **Vescent FFC-100** comb tooth with a
**SLICE-OPL #2** driving a **Brimrose** AOM, and watches the beat with a **Rigol MHO5104** oscilloscope or an
**HP 8563E** spectrum analyzer.

Part of a three-application bench (CREOL, UCF): **Vescent FFC-100 GPS locking** (the comb) ·
**Tunable Laser Stabilization** (this) · **Lab Tools Management** (other instruments).

## Features

* Lock sequence: comb locked → laser on (asks to bring wavelength/power into range) → PLL limits → **beat near
  the target and steady** → servo → monitor (servo held, PLL output off the rails, beat FWHM/offset/movement).
* Rail guard: a railed PLL output breaks the lock and relocks; relock watchdog with an hourly limit.
* Beat monitor on the Laser lock and OPL #2 pages — Rigol (FFT) or HP 8563E, linear power display.
* OPL #2 auto-tune for phase noise, beat FWHM, movement or both (scope or spectrum analyzer).
* Shares instruments safely with Lab Tools Management (claims); command-line tool; full simulator.

## Quick start

```bat
python -m pip install -e .
laser-lock              (or: laser-lock --sim)
laser-lock-cli status
```

## Documentation

* [Installation](docs/installation.md) · [User guide](docs/user-guide.md) · [Configuration](docs/configuration.md)
* [Command-line tool](docs/cli.md) · [Python API guide](docs/api.md) · [API reference](docs/api-reference.md)
* [Instruments](docs/instruments.md) · [Architecture](docs/architecture.md) · [Troubleshooting](docs/troubleshooting.md)
* [Development](docs/development.md) · [Changelog](CHANGELOG.md)

## License

BSD 3-Clause — see [LICENSE](LICENSE) and [NOTICE](NOTICE.md).
