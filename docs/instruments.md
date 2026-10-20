# Instruments

| Role | Instrument | Connection | Notes (bench-verified unless marked) |
|---|---|---|---|
| `opl2` | Vescent SLICE-OPL #2 | USB-serial, `*IDN?` with CR | drives the Brimrose AOM; PLL limits 7–12 V; counter may never see the beat |
| `laser` | HP 8168D/E | GPIB | 8168D grid 100 pm, 8168E 10 pm; coherence control has no GPIB command; check the error queue after writes |
| `laser` | JDSU SWS17101 | GPIB, status-byte read | read termination LF; coherence control write-only; no manual available |
| `scope` | Rigol MHO5104 | USB-TMC | rejected query → empty line; waveform settings only while stopped; `:AUToset`, `:SYSTem:RCLock CINP/COUT/OFF` (programming guide) |
| `sa` | HP 8563E | GPIB, `ID?`/`SER?` (no `*IDN?`) | `FREF EXT/INT`; a preset (`IP`) returns to internal |

**Brimrose VF-450-100 driver**: about 17 MHz/V (400 MHz at 7.2 V, 500 MHz at 13.1 V).
