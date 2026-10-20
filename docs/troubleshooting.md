# Troubleshooting

**An instrument shows "opened …, but the instrument didn't answer".** The VISA address or COM port opened but
nothing replied: check power, the cable and the address (GPIB address on the front panel). Opening an address
always succeeds in VISA, so only an answer counts as connected.

**"in use by …".** Another of the bench applications has that instrument connected. Disconnect it there
(or close that application). A claim left by a crashed application is ignored automatically.

**A VISA instrument hangs the bus (e.g. the Rigol after an interrupted transfer).** Power-cycle the instrument.
The application keeps working: scans run in the background and report "VISA is not answering".

**Nothing found in Devices → Rescan.** Check the instrument is on and that Keysight Connection Expert / NI MAX
sees it. Serial instruments: check Device Manager for the COM port.

**The app won't start from the launcher.** Use option **D** in `launch_apps.bat` to see the error in a console.
"No module named …" → run option **4** (install), or set `CONDA_ENV` to the environment you installed into.

**Where is the log?** Devices → Logs…, or `laserlock.log` next to the settings file.

**"Comb: comb app not running".** Laser Lock reads `comb_status.json` written by Vescent FFC-100 GPS locking;
it's stale after 10 s. Start the comb application, or untick "Require the comb" for tests.

**The OPL #2 counter never shows the beat.** Expected on this bench: locking doesn't need it. The beat instrument
(Rigol or HP 8563E) shows the beat instead.

**"PLL output on the rail".** The servo can't hold the beat; the sequence breaks the lock and relocks (2 tries),
and the page's rail guard does the same while running. Check the beat is within the AOM's reach (beat check
step) and the PLL limits (7–12 V).

**Beat check never passes.** Look at the step's detail: offset from the target and movement. Widen "Within" /
"Moving less than", shorten "For", or bring the laser closer with the wavelength field.
