# Installation

Tunable Laser Stabilization is a Windows desktop application (PySide6 / Qt) written in Python. It also runs on Linux and macOS
for development and with the simulator, but the instrument drivers are tested on Windows.

## Requirements

* Windows 10 or 11
* Python 3.11 or newer (developed on 3.14) — Anaconda or a plain python.org install both work
* A VISA library for GPIB / USB-TMC instruments: Keysight IO Libraries Suite (IVI VISA) or NI-VISA
* GPIB interface for the tunable laser and the HP 8563E (if used)
* USB to SLICE-OPL #2 and the Rigol MHO5104

The Python dependencies (numpy, scipy, PySide6, pyqtgraph, pyserial, pyvisa) are installed
automatically.

## Install

```bat
git clone https://github.com/netadmindave/tunable-laser-stabilization.git
cd tunable-laser-stabilization
python -m pip install -e .
```

`-e` (editable) means updates you pull or unzip into the folder take effect without reinstalling.
For the test suite: `python -m pip install -e .[test]`.

## Launch

```bat
laser-lock                 the application
laser-lock --sim           against the built-in simulator (no hardware)
laser-lock-cli -h              the command-line tool (see docs/cli.md)
```

`python -m laserlock.gui.app` works too.

### Windows launcher (Anaconda)

`launch_apps.bat` (in the folder above the three application folders) activates your conda environment and
offers a menu for all three applications, without console windows. Set `CONDA_ENV` at the top of the file to the
environment you installed into. Its option **4** runs `pip install -e .` in each application folder; **D**
starts an application with a console window, to see why it won't start.

## Check the install

```bat
python -m pytest            (needs the [test] extra; everything runs against the simulator)
laser-lock --sim
```
