# Command-line tool: `laser-lock-cli`

Everything the application does with instruments, from a terminal or a script — no GUI needed.

* Instruments are opened from the roles the GUI saved (Devices… → "Remember these assignments"); nothing is
  scanned unless you run `scan`.
* An instrument another bench application has connected is refused (`in use by …`), never probed.
* Exiting leaves every instrument exactly as it is.
* `--sim` runs against the simulator; `--json` gives machine-readable output (exit code 0 = success,
  1 = error, 2 = not locked / lock failed).

## Quick reference

| Command | What it does |
|---|---|
| `laser-lock-cli roles` | roles, saved instruments, and whether another app has them |
| `laser-lock-cli scan [--save]` | probe every port; `--save` remembers the assignments |
| `laser-lock-cli info ROLE` | identify the instrument and read it once |
| `laser-lock-cli options ROLE [--group TEXT]` | list the instrument's settings (keys, kinds, choices, units) |
| `laser-lock-cli get ROLE [KEY ...]` | read settings (all of them without keys) |
| `laser-lock-cli set ROLE KEY VALUE` | write a setting; prints the read-back |
| `laser-lock-cli do ROLE ACTION` | run an action setting |
| `laser-lock-cli poll ROLE [--every S] [--count N] [--csv FILE]` | log readings (`--count 0` = until Ctrl+C) |
| `laser-lock-cli status` | laser locked? servo, PLL output, rail, comb state (exit 0 = locked, 2 = not) |
| `laser-lock-cli params` | the lock parameters and their defaults (JSON) |
| `laser-lock-cli lock [--params FILE] [--set K=V] [--dry-run] [--yes]` | run the laser lock sequence |

Values: `on`/`off`/`true`/`false`, numbers with SI suffixes (`10M`, `1.5m`, `2e-6`, `50MHz`), or a choice
(short or long form, e.g. `HANN` or `HANNing`).

## Examples

```bat
laser-lock-cli roles
laser-lock-cli status
laser-lock-cli params > lock.json              (edit, then:)
laser-lock-cli lock --params lock.json --yes
laser-lock-cli lock --set beat_role=sa --set beat_still_s=60 --set scope_span_hz=70M --yes
laser-lock-cli set laser wavelength_nm 1550
laser-lock-cli get opl2 pll_min_v pll_max_v
laser-lock-cli poll opl2 --every 0.5 --count 0 --csv opl2.csv
laser-lock-cli --sim lock --set wavelength_nm=1550.1 --set require_comb=off --yes
```

## Complete command reference (`laser-lock-cli -h`)

```text
usage: laser-lock-cli [-h] [--sim] [--settings SETTINGS] [--json]
                      {roles,scan,info,options,get,set,do,poll,lock,params,status}
                      ...

Tunable Laser Stabilization (Laser Lock) — command line. Instruments come from
the roles the GUI saved; nothing is scanned unless you ask.

positional arguments:
  {roles,scan,info,options,get,set,do,poll,lock,params,status}
    roles               list roles, their saved instruments and whether
                        another app has them
    scan                probe every port and show what was found
    info                identify an instrument and read it once
    options             list an instrument's settings
    get                 read settings (all of them if no keys are given)
    set                 write one setting; prints the read-back
    do                  run an action setting (e.g. a preset)
    poll                read an instrument repeatedly
    lock                run the lock sequence (blocking; Ctrl+C stops it)
    params              print the lock parameters with their defaults (JSON)
    status              is it locked right now? (exit code 0 = locked, 2 =
                        not)

options:
  -h, --help            show this help message and exit
  --sim                 use the simulated bench (no hardware)
  --settings SETTINGS   settings file (default: the GUI's)
  --json                machine-readable output
```

### `laser-lock-cli roles`

```text
usage: laser-lock-cli roles [-h]

options:
  -h, --help  show this help message and exit
```

### `laser-lock-cli scan`

```text
usage: laser-lock-cli scan [-h] [--save]

options:
  -h, --help  show this help message and exit
  --save      remember the role assignments (like the GUI)
```

### `laser-lock-cli info`

```text
usage: laser-lock-cli info [-h] role

positional arguments:
  role

options:
  -h, --help  show this help message and exit
```

### `laser-lock-cli options`

```text
usage: laser-lock-cli options [-h] [--group GROUP] role

positional arguments:
  role

options:
  -h, --help     show this help message and exit
  --group GROUP  only groups containing this text
```

### `laser-lock-cli get`

```text
usage: laser-lock-cli get [-h] role [keys ...]

positional arguments:
  role
  keys

options:
  -h, --help  show this help message and exit
```

### `laser-lock-cli set`

```text
usage: laser-lock-cli set [-h] role key value

positional arguments:
  role
  key
  value       on/off, a number (SI suffixes: 10M, 1.5m …) or a choice

options:
  -h, --help  show this help message and exit
```

### `laser-lock-cli do`

```text
usage: laser-lock-cli do [-h] role action

positional arguments:
  role
  action

options:
  -h, --help  show this help message and exit
```

### `laser-lock-cli poll`

```text
usage: laser-lock-cli poll [-h] [--every EVERY] [--count COUNT] [--csv CSV]
                           role

positional arguments:
  role

options:
  -h, --help     show this help message and exit
  --every EVERY  seconds between readings (default 1)
  --count COUNT  number of readings, 0 = until Ctrl+C (default 1)
  --csv CSV      also write the readings to this CSV file
```

### `laser-lock-cli lock`

```text
usage: laser-lock-cli lock [-h] [--params PARAMS] [--set KEY=VALUE]
                           [--dry-run] [--yes]

options:
  -h, --help       show this help message and exit
  --params PARAMS  JSON file with lock parameters (see: params)
  --set KEY=VALUE  override one parameter (repeatable)
  --dry-run        check everything, change nothing
  --yes            answer yes to every question
```

### `laser-lock-cli params`

```text
usage: laser-lock-cli params [-h]

options:
  -h, --help  show this help message and exit
```

### `laser-lock-cli status`

```text
usage: laser-lock-cli status [-h]

options:
  -h, --help  show this help message and exit
```
