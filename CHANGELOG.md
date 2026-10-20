# Changelog

## 0.1.0 + patches 1–15
* Split from benchctl 0.4.0 as a stand-alone installation (patch 1: comb link, Rigol window).
* 2: scope and OPL share the Rigol safely; lock without the counter; scope FWHM monitor; auto-tune FWHM/movement.
* 3: auto-tune "FWHM and movement together". 4: Rigol device clear on connect; retry on startup.
* 5: Devices dialog — background VISA listing, no overlapping buttons. 6: rail detection → break and relock.
* 7: wavelength/power pulled from the laser; range check (1549.9–1550.2 nm, 200 µW–1 mW).
* 8–12: AUX laser settling (added, then removed: didn't work on the bench).
* 9: beat monitor on the Laser lock and OPL #2 pages (separate Rigol window removed).
* 13: shared instrument claims with Lab Tools Management.
* 14: HP 8563E as an alternative beat instrument.
* 15: beat check before the servo (near and steady), 70 MHz default span, linear display, editable values;
  the chosen 10 MHz reference is remembered and applied on connect.
* Command-line tool `laser-lock-cli` (roles, scan, info, options, get, set, do, poll, status, params, lock).
