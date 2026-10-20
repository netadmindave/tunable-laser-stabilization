# API reference — `laserlock`

Generated from the source by importing every module: each public class, function and method with its signature and the first paragraph of its docstring. Built-in add-ons are listed under `laserlock_addons.<id>`, the name scripts import them by (after the add-on loader has run, e.g. via `laserlock.discovery.connect_all()` or `laserlock.addonkit.load_enabled()`).

## Modules

- [`laserlock.addonkit.api`](#laserlock-addonkit-api)
- [`laserlock.addonkit.installer`](#laserlock-addonkit-installer)
- [`laserlock.addonkit.loader`](#laserlock-addonkit-loader)
- [`laserlock.addonkit.manifest`](#laserlock-addonkit-manifest)
- [`laserlock.addonkit.registry`](#laserlock-addonkit-registry)
- [`laserlock.cli`](#laserlock-cli)
- [`laserlock.core.base`](#laserlock-core-base)
- [`laserlock.core.claims`](#laserlock-core-claims)
- [`laserlock.core.options`](#laserlock-core-options)
- [`laserlock.core.serialio`](#laserlock-core-serialio)
- [`laserlock.core.units`](#laserlock-core-units)
- [`laserlock.core.visaio`](#laserlock-core-visaio)
- [`laserlock.datafile`](#laserlock-datafile)
- [`laserlock.discovery`](#laserlock-discovery)
- [`laserlock.dsp`](#laserlock-dsp)
- [`laserlock.gui.app`](#laserlock-gui-app)
- [`laserlock.gui.cards`](#laserlock-gui-cards)
- [`laserlock.gui.connections`](#laserlock-gui-connections)
- [`laserlock.gui.log_window`](#laserlock-gui-log-window)
- [`laserlock.gui.main_window`](#laserlock-gui-main-window)
- [`laserlock.gui.options_panel`](#laserlock-gui-options-panel)
- [`laserlock.gui.page_base`](#laserlock-gui-page-base)
- [`laserlock.gui.pages.overview`](#laserlock-gui-pages-overview)
- [`laserlock.gui.plots`](#laserlock-gui-plots)
- [`laserlock.gui.reference_panel`](#laserlock-gui-reference-panel)
- [`laserlock.gui.theme`](#laserlock-gui-theme)
- [`laserlock.gui.widgets`](#laserlock-gui-widgets)
- [`laserlock.gui.windows.base`](#laserlock-gui-windows-base)
- [`laserlock.gui.worker`](#laserlock-gui-worker)
- [`laserlock.settings`](#laserlock-settings)
- [`laserlock.sim.base`](#laserlock-sim-base)
- [`laserlock.sim.fakeio`](#laserlock-sim-fakeio)
- [`laserlock.sim.world`](#laserlock-sim-world)
- [`laserlock_addons.laser_lock`](#laserlock-addons-laser-lock)
- [`laserlock_addons.laser_lock.autotune`](#laserlock-addons-laser-lock-autotune)
- [`laserlock_addons.laser_lock.beat_check`](#laserlock-addons-laser-lock-beat-check)
- [`laserlock_addons.laser_lock.comb_link`](#laserlock-addons-laser-lock-comb-link)
- [`laserlock_addons.laser_lock.comb_tooth`](#laserlock-addons-laser-lock-comb-tooth)
- [`laserlock_addons.laser_lock.hp8168`](#laserlock-addons-laser-lock-hp8168)
- [`laserlock_addons.laser_lock.hp8563e`](#laserlock-addons-laser-lock-hp8563e)
- [`laserlock_addons.laser_lock.hp8563e_sim`](#laserlock-addons-laser-lock-hp8563e-sim)
- [`laserlock_addons.laser_lock.laser_sequence`](#laserlock-addons-laser-lock-laser-sequence)
- [`laserlock_addons.laser_lock.laser_setpoints`](#laserlock-addons-laser-lock-laser-setpoints)
- [`laserlock_addons.laser_lock.opl_sim`](#laserlock-addons-laser-lock-opl-sim)
- [`laserlock_addons.laser_lock.overview`](#laserlock-addons-laser-lock-overview)
- [`laserlock_addons.laser_lock.pages.beat_monitor`](#laserlock-addons-laser-lock-pages-beat-monitor)
- [`laserlock_addons.laser_lock.pages.laser`](#laserlock-addons-laser-lock-pages-laser)
- [`laserlock_addons.laser_lock.pages.opl`](#laserlock-addons-laser-lock-pages-opl)
- [`laserlock_addons.laser_lock.pages.opl2`](#laserlock-addons-laser-lock-pages-opl2)
- [`laserlock_addons.laser_lock.pages.process`](#laserlock-addons-laser-lock-pages-process)
- [`laserlock_addons.laser_lock.rigol_mho5104`](#laserlock-addons-laser-lock-rigol-mho5104)
- [`laserlock_addons.laser_lock.scope_owner`](#laserlock-addons-laser-lock-scope-owner)
- [`laserlock_addons.laser_lock.sim`](#laserlock-addons-laser-lock-sim)
- [`laserlock_addons.laser_lock.sliceopl`](#laserlock-addons-laser-lock-sliceopl)
- [`laserlock_addons.laser_lock.sws17101`](#laserlock-addons-laser-lock-sws17101)

## `laserlock.addonkit.api`

The object every add-on's ``register(api)`` receives.

```python
from laserlock.addonkit import api
```

### class `AddonAPI(info, registry=Registry(addons={laser_lock: AddonInfo(id=laser_lock, name=Laser lock, path=PosixPath('/home/claude/w/laserlock/laserlock/addons/laser_lock'), version='1.1.0', type=module, category=Modules, description='SLICE-OPL #2 driving the Brimrose AOM, the tunable laser (HP 8168D/E, JDSU SWS17101), the Rigol MHO5104, and the laser lock process. Reads the comb state from the Vescent Comb app.', author=Dave Smith, requires=['pyserial>=3.5', 'pyvisa>=1.11'], depends=[], optional=[], laserlock='', entry=register, default_enabled=True, builtin=True, enabled=True, state=loaded, error='', missing=[], overrides_builtin=False)}, roles={opl2: RoleSpec(role=opl2, label='OPL #2 · laser → Brimrose', kinds=[sliceopl], addon=laser_lock, capabilities=(opl,), poll_s=1.0, bench_row=False, order=20), laser: RoleSpec(role=laser, label=Tunable laser, kinds=[hp8168, sws17101], addon=laser_lock, capabilities=(tunable_laser,), poll_s=2.0, bench_row=False, order=21), scope: RoleSpec(role=scope, label='Oscilloscope · Rigol MHO5104', kinds=[rigol_mho5104], addon=laser_lock, capabilities=(scope,), poll_s=2.0, bench_row=True, order=30), sa: RoleSpec(role=sa, label='Spectrum analyzer · HP 8563E (beat instrument)', kinds=[hp8563e], addon=laser_lock, capabilities=(spectrum,), poll_s=3.0, bench_row=True, order=34)}, drivers={sliceopl: DriverSpec(kind=sliceopl, cls=<class laserlock_addons.laser_lock.sliceopl.SliceOPL>, label='Vescent SLICE-OPL', addon=laser_lock, package=laserlock_addons.laser_lock), hp8168: DriverSpec(kind=hp8168, cls=<class laserlock_addons.laser_lock.hp8168.HP8168>, label='HP 8168D/E tunable laser', addon=laser_lock, package=laserlock_addons.laser_lock), sws17101: DriverSpec(kind=sws17101, cls=<class laserlock_addons.laser_lock.sws17101.SWS17101>, label=JDSU SWS17101 tunable laser, addon=laser_lock, package=laserlock_addons.laser_lock), rigol_mho5104: DriverSpec(kind=rigol_mho5104, cls=<class laserlock_addons.laser_lock.rigol_mho5104.RigolMHO5104>, label=Rigol MHO5104 oscilloscope, addon=laser_lock, package=laserlock_addons.laser_lock), hp8563e: DriverSpec(kind=hp8563e, cls=<class laserlock_addons.laser_lock.hp8563e.HP8563E>, label=HP 8563E, addon=laser_lock, package=laserlock_addons.laser_lock)}, serial_probes=[SerialProbe(name='Vescent SLICE-OPL *IDN?', match=<function _vescent_port>, probe=<function _probe_opl>, exclusive=False, priority=60, addon=laser_lock)], visa_classifiers=[(<function _classify>, laser_lock), (<function _sa_classify>, laser_lock)], visa_probes=[VisaSilentProbe(name='HP 85xx ID?/SER?', probe=<function _sa_probe>, priority=40, addon=laser_lock), VisaSilentProbe(name='SWS17101 status-byte read', probe=<function _probe_sws>, priority=60, addon=laser_lock)], scanners=[], openers={sliceopl: <function AddonAPI.serial_opener.<locals>.open_ at 0x7f4c05b8e3e0>}, on_connect={hp8168: [<function _apply_grid>]}, pages=[UISpec(key=laserlock, label=Laser lock, cls='pages.process:LaserLockPage', role=None, section=LASER LOCK, order=20, addon=laser_lock, package=laserlock_addons.laser_lock), UISpec(key=opl2, label='SLICE-OPL #2 · laser', cls='pages.opl2:OPL2Page', role=opl2, section=LASER LOCK, order=21, addon=laser_lock, package=laserlock_addons.laser_lock), UISpec(key=laser, label=Tunable laser, cls='pages.laser:LaserPage', role=laser, section=LASER LOCK, order=22, addon=laser_lock, package=laserlock_addons.laser_lock)], windows=[], overview=[UISpec(key=opl2, label=card, cls='overview:OPL2Card', role=None, section='', order=20, addon=laser_lock, package=laserlock_addons.laser_lock), UISpec(key=laser, label=card, cls='overview:LaserCard', role=None, section='', order=21, addon=laser_lock, package=laserlock_addons.laser_lock)], chain=[ChainSpec(key=comb, caption='Comb (Vescent Comb app)', role=opl2, update=<function _pill_comb>, order=10, addon=laser_lock), ChainSpec(key=laser, caption='Laser → comb · OPL #2', role=opl2, update=<function _pill_laser>, order=20, addon=laser_lock)], safe_standby=[(laser, tunable laser output OFF)], summaries={scope: <function _scope_summary>, sa: <function _sa_summary>}, sim_hooks=[(<function AddonAPI.add_sim.<locals>.<lambda> at 0x7f4bfff619e0>, laser_lock)], menu_actions=[], references=[RefSpec(role=scope, input=rear 10 MHz REF IN, mode=switch, status=<function register.<locals>.<lambda> at 0x7f4c0069e8e0>, option=ext_ref, detail=None, note=':SYSTem:RCLock', addon=laser_lock), RefSpec(role=opl2, input='REF IN (GPS 10 MHz)', mode=always, status=<function register.<locals>._opl2_ref at 0x7f4c0069e480>, option=None, detail=<function register.<locals>.<lambda> at 0x7f4bfff61760>, note=reference measured by the OPL, addon=laser_lock), RefSpec(role=sa, input=rear J9 10 MHz REF IN, mode=switch, status=<function register.<locals>.<lambda> at 0x7f4bfff61800>, option=ext_ref, detail=None, note='FREF EXT/INT', addon=laser_lock)]))`

- `add_device(self, kind: str, cls, label: str = '') -> None` — An instrument driver class (subclass of laserlock.Device).
- `add_role(self, role: str, label: str, kinds: Iterable[str], capabilities: Iterable[str] = (), poll_s: Any = 1.0, bench_row: bool = False, order: int = 100) -> None` — A job on the bench ("opl2", "scope", "sa"…). Calling it again for an existing role adds kinds, so a second add-on can plug a new instrument model into a role another add-on owns.
- `add_serial_probe(self, name: str, match: Callable, probe: Callable, exclusive: bool = False, priority: int = 50) -> None` — Identify a USB-serial port. ``match(PortInfo)`` decides from VID/PID only (no bytes sent).
- `add_visa_classifier(self, fn: Callable[[str], Optional[str]]) -> None` — ``fn(idn_string) -> kind | None`` for instruments that answer *IDN?.
- `add_visa_probe(self, name: str, probe: Callable, priority: int = 50) -> None` — For GPIB instruments that do NOT answer *IDN? (``probe(inst, resource, bus, opts)``).
- `add_scanner(self, name: str, label: str, scan: Callable) -> None` — Anything that isn't serial or VISA (Ethernet discovery, a drive, …).
- `add_opener(self, kind: str, fn: Callable) -> None` — How to open a found instrument. Serial instruments use ``serial_opener``; VISA ones need none.
- `on_connect(self, kind: str, fn: Callable[[Any, Any], None]) -> None` — Called with (device, settings) right after the GUI opens an instrument of this kind.
- `add_safe_standby(self, role: str, description: str) -> None` — Safe standby / quit call ``safe_state()`` on this role (laser output off, emission off …).
- `add_page(self, key: str, label: str, cls, role: Optional[str] = None, section: str = '', order: int = 100) -> None` — A page in the main window's navigation (``cls`` subclasses laserlock.gui.page_base.Page).
- `add_window(self, key: str, label: str, cls, role: Optional[str] = None, order: int = 100) -> None` — A separate instrument window (``cls`` subclasses laserlock.gui.windows.base.InstrumentWindow).
- `add_overview_panel(self, key: str, cls, span: str = card, order: int = 100) -> None` — A panel on the Overview page. ``span`` is "card" (one grid cell) or "wide" (full row).
- `add_chain_pill(self, key: str, caption: str, role: str, update: Callable, order: int = 100) -> None` — A status pill in the top lock-chain bar, updated from ``role``'s polls.
- `add_summary(self, role: str, fn: Callable[[Dict[str, Any]], str]) -> None` — One-line live summary for the Overview "Bench instruments" table.
- `add_reference(self, role: str, input: str, mode: str = switch, status=None, option: Optional[str] = None, detail=None, note: str = '') -> None` — Declare how ``role`` uses the 10 MHz (GPS) reference, for the Overview reference list.
- `add_menu_action(self, menu: str, label: str, fn: Callable[[Any], None]) -> None` — An entry in the main menu bar; ``fn(main_window)``.
- `add_sim(self, fn) -> None` — ``fn(world)`` adds this add-on's simulated instruments (``"sim:install"`` string is fine).
- `resolve(self, spec)`
- static `serial_opener(cls, baudrate: int = 115200, timeout: float = 1.0, **kw) -> Callable` — Opener for drivers whose constructor takes ``(port, ser=...)``.

## `laserlock.addonkit.installer`

Requirement checks and pip installs for add-ons.

```python
from laserlock.addonkit import installer
```

### `is_satisfied(req: str) -> bool`

True when the distribution is installed (and the version matches, when packaging is available).

### `missing(reqs: List[str]) -> List[str]`

### `pip_command(reqs: List[str]) -> List[str]`

### `pip_install(reqs: List[str], log: Optional[Callable[[str], None]] = None, timeout: float = 900) -> Tuple[bool, str]`

Install with the same Python that runs laserlock. Returns (ok, combined output).

## `laserlock.addonkit.loader`

Find add-on folders, check/install their requirements, import them and call ``register(api)``.

```python
from laserlock.addonkit import loader
```

**Constants:** `NAMESPACE`

### `addon_dirs(settings=None) -> List[Path]`

### `create_from_template(dest_dir: Path, addon_id: str, name: str, cls_name: str = '', role: str = '', kind: str = '') -> Path`

Copy the template add-on to ``dest_dir/addon_id`` with names filled in.

### `default_user_dir() -> Path`

### `ensure_loaded(settings=None, **kw) -> None`

Load the enabled add-ons once per process (scripts get this through discovery). Without ``settings`` the user's settings file decides which add-ons are on, as in the GUI.

### `last_scan() -> Dict[str, AddonInfo]`

### `load(addon_id: str, settings=None, auto_install: bool = True, log=<built-in function print>)`

Load one add-on (and what it depends on) even if it is unchecked; return its package.

### `load_enabled(settings=None, auto_install: Optional[bool] = None, installer=None, log=None, include_all: bool = False, only: Optional[Iterable[str]] = None) -> Dict[str, AddonInfo]`

Load every enabled add-on (dependencies first). ``include_all`` ignores the checkboxes.

### `load_one(info: AddonInfo, settings=None, auto_install: bool = True, installer=None, log: Optional[Callable[[str], None]] = None) -> AddonInfo`

### `reset() -> None`

Forget every loaded add-on (tests, or before a reload).

### `scan(settings=None) -> Dict[str, AddonInfo]`

Read every manifest (no add-on code is imported). Returns {id: AddonInfo} in display order.

### `user_dirs(settings=None) -> List[Path]`

## `laserlock.addonkit.manifest`

Add-on manifests (``addon.toml``) — read without importing any add-on code.

```python
from laserlock.addonkit import manifest
```

**Constants:** `MANIFEST`

### class `AddonInfo(id: str, name: str, path: Path, version: str = '0.0.0', type: str = tool, category: str = Instruments, description: str = '', author: str = '', requires: List[str] = <factory>, depends: List[str] = <factory>, optional: List[str] = <factory>, laserlock: str = '', entry: str = register, default_enabled: bool = True, builtin: bool = False, enabled: bool = False, state: str = not loaded, error: str = '', missing: List[str] = <factory>, overrides_builtin: bool = False) -> None`

Everything the manager shows about one add-on folder.

- `module_name` *(property)*
- `label` *(property)*

### `load_toml(path: Path) -> Dict[str, Any]`

### `read_manifest(folder: Path, builtin: bool = False) -> Optional[AddonInfo]`

## `laserlock.addonkit.registry`

What the loaded add-ons contribute. The shell (discovery, GUI, simulator) reads only this.

```python
from laserlock.addonkit import registry
```

### class `ChainSpec(key: str, caption: str, role: str, update: Callable[[Dict[str, Any], Any], Optional[Tuple[str, str]]], order: int = 100, addon: str = '') -> None`


### class `DriverSpec(kind: str, cls: Any, label: str, addon: str = '', package: str = '') -> None`

- `get(self)`

### class `RefSpec(role: str, input: str, mode: str = switch, status: Optional[Callable[[Dict[str, Any]], Optional[bool]]] = None, option: Optional[str] = None, detail: Optional[Callable[[Dict[str, Any]], str]] = None, note: str = '', addon: str = '') -> None`

How one instrument uses the shared 10 MHz (GPS) reference — shown in the Overview list.


### class `Registry(addons: Dict[str, Any] = <factory>, roles: Dict[str, RoleSpec] = <factory>, drivers: Dict[str, DriverSpec] = <factory>, serial_probes: List[SerialProbe] = <factory>, visa_classifiers: List[Tuple[Callable[[str], Optional[str]], str]] = <factory>, visa_probes: List[VisaSilentProbe] = <factory>, scanners: List[Scanner] = <factory>, openers: Dict[str, Callable[[Any], Any]] = <factory>, on_connect: Dict[str, List[Callable[[Any, Any], None]]] = <factory>, pages: List[UISpec] = <factory>, windows: List[UISpec] = <factory>, overview: List[UISpec] = <factory>, chain: List[ChainSpec] = <factory>, safe_standby: List[Tuple[str, str]] = <factory>, summaries: Dict[str, Callable[[Dict[str, Any]], str]] = <factory>, sim_hooks: List[Tuple[Callable[[Any], None], str]] = <factory>, menu_actions: List[Tuple[str, str, Callable[[Any], None], str]] = <factory>, references: List[RefSpec] = <factory>) -> None`

- `clear(self)`
- `roles_for_kind(self, kind: str) -> List[str]`
- `roles_with(self, capability: str) -> List[str]`
- `driver(self, kind: str)`
- `role_label(self, role: str) -> str`

### class `RoleSpec(role: str, label: str, kinds: List[str], addon: str = '', capabilities: Tuple[str, ...] = (), poll_s: Any = 1.0, bench_row: bool = False, order: int = 100) -> None`

- `poll_interval(self, settings) -> float`

### class `Scanner(name: str, label: str, scan: Callable[[Any], List[Any]], addon: str = '') -> None`


### class `SerialProbe(name: str, match: Callable[[Any], bool], probe: Callable[[Any, Any], Any], exclusive: bool = False, priority: int = 50, addon: str = '') -> None`


### class `UISpec(key: str, label: str, cls: Any, role: Optional[str] = None, section: str = '', order: int = 100, addon: str = '', package: str = '') -> None`

- `get(self)`

### class `VisaSilentProbe(name: str, probe: Callable[..., Any], priority: int = 50, addon: str = '') -> None`


### `resolve(spec, package: str)`

'module:Name' relative to an add-on package -> object (or pass objects through).

## `laserlock.cli`

Tunable Laser Stabilization (Laser Lock) — command-line tool.

```python
from laserlock import cli
```

**Constants:** `COMMANDS`, `EXIT_ERROR`, `EXIT_FAILED`, `EXIT_OK`

### class `Ctx(args)`

- `out(self, obj, text: Optional[str] = None)`
- `found_for(self, role: str)` — The saved instrument for ``role`` (no scan); in --sim mode, or if nothing is saved, a scan.
- `open(self, role: str)`
- `close(self)`

### `build_parser(extra=None) -> argparse.ArgumentParser`

### `cmd_do(ctx, a)`

### `cmd_get(ctx, a)`

### `cmd_info(ctx, a)`

### `cmd_lock(ctx, a)`

### `cmd_options(ctx, a)`

### `cmd_params(ctx, a)`

### `cmd_poll(ctx, a)`

### `cmd_roles(ctx, a)`

### `cmd_scan(ctx, a)`

### `cmd_set(ctx, a)`

### `cmd_status(ctx, a)`

### `main(argv=None) -> int`

### `run(argv=None, extra_parsers=None, extra_commands=None) -> int`

## `laserlock.core.base`

Common base for every instrument driver.

```python
from laserlock.core import base
```

### class `Device() -> None`

Base class. Subclasses set ``KIND`` and implement the hooks below.

- `close(self) -> None`
- `safe_state(self) -> None` — Put the instrument in a state that is safe to walk away from.
- `identify(self) -> Identity`
- `snapshot(self) -> Dict[str, Any]`
- `poll(self) -> Dict[str, Any]` — Fast status read used by the GUI at ~1 Hz. Defaults to snapshot().
- `restore(self, snap: Dict[str, Any], keys: Optional[Iterable[str]] = None) -> Dict[str, str]` — Write back restorable settings from a snapshot.
- `diff(self, saved: Dict[str, Any], keys: Optional[Iterable[str]] = None, rel_tol: float = 1e-09) -> Dict[str, tuple]` — Compare live settings against a saved snapshot -> {key: (live, saved)}.
- class `find(cls, serial: Optional[str] = None, **kw)` — Locate this instrument (by USB ID / *IDN? / serial) and open it.

### class `DeviceError(…)`

Instrument did not respond, rejected a command, or returned garbage.

### class `Identity(kind: str, model: str = '', serial: str = '', firmware: str = '', raw: str = '', extra: Dict[str, Any] = <factory>) -> None`

- `as_dict(self) -> Dict[str, Any]`
- `key` *(property)* — Stable key used to match a physical unit to a role.

### class `SafetyError(…)`

A request was refused because it would violate a hard safety rule.

## `laserlock.core.claims`

Cross-app instrument claims: an instrument connected in one app can't be connected in another.

```python
from laserlock.core import claims
```

**Constants:** `APP`

### class `InUse(address: str, app: str)`


### `claim(address: str) -> Optional[str]`

Claim the instrument for this app. Returns None on success, or the name of the app holding it.

### `folder() -> Path`

### `holder(address: str) -> Optional[str]`

Name of another running app that holds this instrument, else None.

### `key(address: str) -> str`

One key per physical instrument: USB VISA resources by vendor/product/serial (the '::0::' interface number and suffix are dropped), everything else by its normalised address.

### `release(address: str) -> None`

### `release_all() -> None`

## `laserlock.core.options`

Declarative instrument options.

```python
from laserlock.core import options
```

### class `Opt(key: str, label: str, group: str = General, kind: str = number, get: Getter = None, set: Setter = None, choices: Sequence = (), unit: str = '', lo: Optional[float] = None, hi: Optional[float] = None, tip: str = '', bools: Tuple[str, str] = (ON, OFF), parse: Optional[Callable[[str], Any]] = None, scale: float = 1.0, indexed: bool = False) -> None`

- `readonly` *(property)*
- `pairs(self) -> List[Tuple[str, Any]]`
- `convert(self, raw: Any) -> Any` — Instrument reply → Python value of this option's kind.
- `encode(self, value: Any) -> str` — Python value → text substituted for ``{v}`` in a SCPI ``set`` string.

### class `OptionsMixin()`

Mixed into :class:`laserlock.core.base.Device`. Override ``options()`` for dynamic tables.

- `options(self) -> List[Opt]`
- `option(self, key: str) -> Opt`
- `option_query(self, cmd: str) -> Optional[str]`
- `option_write(self, cmd: str) -> None`
- `read_option(self, key: str) -> Any`
- `write_option(self, key: str, value: Any = None, readback: bool = True) -> Any`
- `read_options(self, keys: Optional[Iterable[str]] = None, group: Optional[str] = None) -> Dict[str, Any]`

### `match_choice(raw: Any, values: Iterable[Any]) -> Any`

Map an instrument reply onto one of ``values`` (exact, numeric, or SCPI short/long form).

## `laserlock.core.serialio`

Serial helpers: an ASCII line transport and a port lister.

```python
from laserlock.core import serialio
```

### class `PortInfo(device: str, description: str = '', hwid: str = '', vid: Optional[int] = None, pid: Optional[int] = None, serial_number: str = '', manufacturer: str = '') -> None`

- `is_bluetooth` *(property)*
- `usb_family` *(property)* — Rough chip family from the USB vendor ID.

### class `SerialLine(port: Optional[str] = None, baudrate: int = 115200, timeout: float = 1.0, eol: str = '\r', quiet: float = 0.05, ser=None)`

Thread-safe ASCII command/response transport.

- `timeout` *(property)*
- `write(self, cmd: str) -> None`
- `read(self, timeout: Optional[float] = None) -> str` — Wait for the reply to begin, then drain until the line goes quiet.
- `query(self, cmd: str, timeout: Optional[float] = None) -> str`
- `close(self) -> None`
- `is_open` *(property)*

### `list_serial_ports() -> List[PortInfo]`

## `laserlock.core.units`

Small unit helpers shared by drivers and the GUI.

```python
from laserlock.core import units
```

**Constants:** `C_LIGHT`

### `ceil_125(val: float) -> float`

Smallest 1-2-5 value ≥ val.

### `dbm_to_w(dbm: float) -> float`

### `eng(value: float, unit: str = '', digits: int = 4) -> str`

Engineering notation in powers of three: eng(2.5e7,'Hz') -> '25 MHz'.

### `first_125_below(val: float) -> float`

Largest 1-2-5 step strictly below val.

### `nm_to_thz(nm: float) -> float`

### `seq_125(lo: float, hi: float)`

Every 1-2-5 value from lo to hi inclusive (scope V/div and s/div steps).

### `snap_125(val: float) -> float`

Nearest value on the 1-2-5 sequence.

### `snap_to_grid(value: float, step: float, origin: float = 0.0) -> float`

Nearest multiple of ``step`` (rounding up or down, whichever is closer).

### `thz_to_nm(thz: float) -> float`

### `w_to_dbm(w: float) -> float`

## `laserlock.core.visaio`

VISA helpers: a shared resource manager and a thread-safe instrument wrapper.

```python
from laserlock.core import visaio
```

### class `VisaInstrument(resource: Optional[str] = None, inst=None, timeout_ms: int = 5000, read_termination: Optional[str] = '\n', write_termination: str = '\n')`

Thin wrapper adding a lock, safe queries and timeout scoping.

- `write(self, cmd: str) -> None`
- `read(self) -> str`
- `query(self, cmd: str, timeout_ms: Optional[int] = None) -> str`
- `try_query(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[str]` — Query that returns None on timeout instead of raising.
- `query_float(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[float]`
- `read_raw(self) -> bytes`
- `query_binary_values(self, cmd: str, **kw)`
- `read_stb(self) -> int`
- `clear(self) -> None`
- `set_timeout(self, ms: int) -> None`
- `close(self) -> None`
- `sleep(self, s: float) -> None`

### `resource_manager(backend: Optional[str] = None)`

One ResourceManager per process (opening several confuses NI-VISA).

### `set_resource_manager(rm) -> None`

Inject a resource manager (used by the simulator).

## `laserlock.datafile`

Data files with the bench state in a header.

```python
from laserlock import datafile
```

### class `CSVLog(path: str, kind: str = log, meta: Optional[Dict[str, Any]] = None)`

Append-mode CSV (REC logs, scans): header written once when the file is created.

- `write(self, row: Dict[str, Any]) -> None`
- `close(self) -> None`

### `base_metadata(kind: str = '') -> Dict[str, Any]`

### `bench_metadata(bench) -> Dict[str, Any]`

Metadata for scripts: every open device's snapshot (read-only) under ``instruments``.

### `current_metadata(kind: str = '', extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

### `header_lines(meta: Dict[str, Any]) -> List[str]`

``# key: value`` lines; nested values are JSON on one line.

### `read_header(path: str) -> Dict[str, Any]`

The ``# key: value`` header of a laserlock CSV back as a dict.

### `set_provider(fn: Optional[Callable[[], Dict[str, Any]]]) -> None`

Register a function returning the current bench state (the GUI does this).

### `write_csv(path: str, header: Sequence[str], columns: Optional[Sequence[Iterable]] = None, rows: Optional[Iterable[Sequence]] = None, kind: str = '', meta: Optional[Dict[str, Any]] = None, fmt: str = '{:.10g}') -> str`

Write a CSV with the metadata header. Give ``columns`` (one iterable per column) or ``rows``.

## `laserlock.discovery`

Find every instrument, identify it, and match it to its role by serial number.

```python
from laserlock import discovery
```

### class `Bench(devices: Dict[str, Any], scan: ScanResult, errors: Dict[str, str])`

Connected devices by role. ``bench.opl1``, ``bench.laser`` …

- `close(self) -> None` — Safe state + close for every device.

### class `Found(kind: str, address: str, bus: str, model: str = '', serial: str = '', firmware: str = '', how: str = '', raw: str = '', extra: Dict[str, Any] = <factory>, role: str = '', status: str = new, previous_address: str = '') -> None`

- `label` *(property)*
- `as_dict(self) -> Dict[str, Any]`

### class `Hooks()`

Indirection points so the simulator (or tests) can stand in for hardware.

- `reset(self)`
- `get(self, name: str, default=None)`
- `set(self, name: str, value) -> None`

### class `ScanOptions(skip_bluetooth: bool = True, serial: bool = True, visa: bool = True, serial_timeout: float = 0.5, visa_timeout_ms: int = 300, probe_exclusive_ports: bool = False, exclude: tuple = (), scanners: Dict[str, bool] = <factory>) -> None`


### class `ScanResult(found: List[Found] = <factory>, skipped: List[Found] = <factory>, unknown: List[Found] = <factory>, duration_s: float = 0.0, assignments: Dict[str, Found] = <factory>, missing: Dict[str, Dict[str, Any]] = <factory>) -> None`

- `by_kind(self, kind: str) -> List[Found]`

### `assign_roles(result: ScanResult, saved_roles: Optional[Dict[str, Dict[str, Any]]] = None) -> ScanResult`

Match found devices to roles: by (kind, serial) first, then by kind.

### `classify_idn(idn: str) -> Optional[str]`

### `connect_all(settings=None, opts: Optional[ScanOptions] = None, roles=None, remember: bool = True, progress=None) -> Bench`

Scan, match roles (by serial, from the settings file), open everything.

### `idn_query(port: str, eol: str, timeout: float, baudrate: int = 115200, quiet: float = 0.05) -> str`

``*IDN?`` on a serial port with the given line ending ('' on no reply).

### `open_found(f: Found) -> Any`

Open a found instrument with its add-on's opener (VISA instruments need none). Claims it first: if another app has it connected, raises ``claims.InUse`` without touching it.

### `open_one(kind: str, serial: Optional[str] = None, opts: Optional[ScanOptions] = None)`

Scan and open the first instrument of ``kind`` (optionally with ``serial``).

### `probe_visa_resource(rm, res: str, opts: ScanOptions) -> Found`

### `remember_roles(result: ScanResult, settings) -> None`

### `reopen(f: Found) -> Any`

Open ``f`` again after it dropped off the bus (auto-reconnect).

### `scan_all(opts: Optional[ScanOptions] = None, progress: Optional[Callable[[str], None]] = None, already_open: Optional[List[Found]] = None) -> ScanResult`

``already_open``: Found records of devices this session has open; they are listed without being probed again (an open COM port cannot be re-opened).

### `scan_serial(opts: ScanOptions) -> Tuple[List[Found], List[Found], List[Found]]`

### `scan_visa(opts: ScanOptions) -> Tuple[List[Found], List[Found]]`

### `split_idn(idn: str) -> List[str]`

### `with_serial(port: str, baudrate: int, timeout: float, fn)`

Open ``port`` through the hook, run ``fn(ser)``, always close. Exceptions -> None.

## `laserlock.dsp`

Signal metrics shared by the beat check, auto-tune and frequency monitor.

```python
from laserlock import dsp
```

**Constants:** `FFT_UNITS`, `FFT_WINDOWS`

### `amplitude_spectrum(v: np.ndarray, dt: float, window: str = hann, unit: str = dBV, impedance: float = 50.0)`

Single-sided amplitude spectrum of a real record.

### `carrier_to_pedestal_db(f: np.ndarray, p_dbm: np.ndarray, f0: float, exclude_hz: float, pedestal_hz: float) -> float`

Carrier minus median pedestal level within ±pedestal_hz (higher is better).

### `integrated_phase_rms(v: np.ndarray, dt: float, f0: Optional[float] = None, band: Tuple[float, float] = (10.0, 1000000.0)) -> float`

RMS residual phase (rad) integrated over ``band`` (lower is better).

### `overlapping_adev(y_frac: Sequence[float], tau0: float, ms: Iterable[int] = (1, 2, 4, 8, 16))`

Overlapping Allan deviation of fractional-frequency samples.

### `peak_frequency_fft(v: np.ndarray, dt: float, fmin: float = 0.0, fmax: Optional[float] = None) -> float`

Dominant frequency: Hann window + parabolic interpolation (from the notebook).

### `quicklook(v: np.ndarray, dt: float, expected_hz: float, search_hz: float = 1000000.0)`

Sub-bin frequency estimate. Returns (f_hz, sigma_f_hz, snr_db).

### `residual_phase(v: np.ndarray, dt: float, f0: Optional[float] = None, lp_hz: Optional[float] = None) -> np.ndarray`

Demodulate at f0 and return the detrended, unwrapped phase (rad).

### `servo_bump_db(f: np.ndarray, p_dbm: np.ndarray, f0: float, inner_hz: float = 10000.0, outer_hz: float = 1000000.0) -> float`

Highest point in the servo-bump annulus relative to the carrier (lower is better).

## `laserlock.gui.app`

Entry point: ``python -m laserlock.gui [--sim] [--settings PATH] [--no-scan]``.

```python
from laserlock.gui import app
```

### `install_wheel_guard(app)`

Number fields and dropdowns never change with the mouse wheel; the wheel scrolls the page instead.

### `main(argv=None) -> int`

## `laserlock.gui.cards`

Reusable Overview building blocks for add-ons.

```python
from laserlock.gui import cards
```

### class `OverviewPanel(hub, settings, main=None, title: str = '', right=None)`

Base for anything placed on the Overview page by an add-on.

- `on_poll(self, role: str, d: Dict[str, Any]) -> None`
- `on_devices_changed(self) -> None`

### class `RoleCard(hub, settings, main=None)`

- `transform(self, d: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]`
- `on_devices_changed(self)`
- `on_poll(self, role, d)`

## `laserlock.gui.connections`

Startup dialog: scan, show what was found, assign roles (by serial), connect.

```python
from laserlock.gui import connections
```

**Constants:** `STATUS`

### class `ConnectionsDialog(parent, settings, simulated: bool = False, already_open=None, identify_hook=None, failed=None, connected=None)`

- `options(self) -> ScanOptions`
- `rescan(self)`
- `chosen(self)` — role -> Found from the combo boxes (scanned, saved, already connected, or a port picked by hand).
- `disconnect_one(self, role)`
- `reconnect_one(self, role)`
- `connect_one(self, role)`
- `swap_opls(self)`
- `identify(self, role)`
- `offline(self)`

## `laserlock.gui.log_window`

Logs window: everything the app logs, for troubleshooting.

```python
from laserlock.gui import log_window
```

**Constants:** `COLORS`, `LEVELS`

### class `LogBuffer(maxlen: int = 20000)`

Process-wide log store (thread-safe enough: deque appends are atomic; Qt signal is queued).

- `open_file(self, folder: str)`
- `add(self, level: str, source: str, text: str)`

### class `LogWindow(settings=None)`

- `refill(self)`
- `copy(self)`
- `save(self)`

### `attach_hub(hub)`

Event log and device states from the GUI hub.

### `install(log_folder: str = '')`

Start capturing (call once, early).

## `laserlock.gui.main_window`

Main window shell: lock-chain bar, navigation, pages, status bar, instrument windows.

```python
from laserlock.gui import main_window
```

### class `ChainPill(caption: str)`

- `set(self, text: str, state: str)`

### class `MainWindow(settings, simulated: bool = False)`

- `page_specs` *(property)*
- `window_specs` *(property)*
- `show_page(self, key)`
- `open_window(self, key)`
- `startup(self)` — Connect the devices saved last time, at their saved addresses — no scan. Anything that does not answer is listed in the device finder with the free ports it could be on.
- `open_finder(self, failed=None)` — Device finder. It does not scan by itself: it shows the saved assignments and the free ports for each role; press Rescan to probe.
- `connect_found(self, chosen, scan, remember=True, opened=None, only=False, on_done=None, after=None)` — Connect ``chosen`` roles. Opening instruments (and their on-connect hooks) runs in a background thread, so a slow or hung port never freezes the window. ``only=True`` leaves other roles alone.
- `connect_role(self, role, f, on_done=None, after=None)` — Connect one role now (the device finder's per-device Connect button). ``after``: an Event to wait for first (the previous connection closing), waited for in the background.
- `disconnect_role(self, role)` — Close one role without touching the instrument; returns an Event set when it's closed.
- `assign_unit(self, role, kind, serial)` — Point ``role`` at the unit with ``serial`` (OPL / laser dropdowns).
- `open_logs(self)`
- `switch_to_sim(self)`
- `metadata(self)` — Bench state written into the header of every data file (laserlock.datafile).
- `after_lock_sequence(self)` — Pages re-read their instruments after a sequence changed them.
- `toggle_rec(self, on)`
- `safe_standby(self)`
- `open_data_folder(self)`
- `change_data_folder(self)`
- `restart(self)` — Close (instruments left exactly as they are) and start again.
- `closeEvent(self, e)` — Close and leave every instrument exactly as it is (outputs, locks, servos). The next start reconnects to the saved devices without changing them.

### `saved_found(role: str, s: dict)`

A discovery.Found rebuilt from a saved role entry (no scan).

## `laserlock.gui.options_panel`

Setup tab built from a driver's ``OPTIONS`` table (see laserlock.core.options).

```python
from laserlock.gui import options_panel
```

### class `OptionsPanel(hub, role: str, columns: int = 2, intro: str = '', groups: Optional[List[str]] = None, exclude_groups: Optional[List[str]] = None)`

- `refresh(self)`
- `showEvent(self, e)` — Options are read the first time the tab is actually shown, not when the window opens (some instruments flag an error for every setting they don't support).
- `write(self, key: str, value: Any)`
- `read_one(self, key: str)`
- `read_all(self)`

## `laserlock.gui.page_base`

Base class for main-window pages.

```python
from laserlock.gui import page_base
```

### class `Page(hub, settings, main=None)`

A scrollable page bound to one or more roles. Subclasses build ``self.content``.

- `header(self, title: str, sub: str = '', pills=(), buttons=())`
- `on_poll(self, role: str, data: dict)`
- `on_devices_changed(self)`
- `call(self, fn, on_done=None, log=None, role=None)`
- `connected` *(property)*
- `save_snapshot_csv(self, role: Optional[str] = None)`
- `remember_state(self, role: Optional[str] = None)` — Read the device snapshot and store it as 'last session' in the settings file.
- `restore_last_session(self, role: Optional[str] = None)`

## `laserlock.gui.pages.overview`

Overview: panels contributed by the add-ons, the bench-instrument table and the event log.

```python
from laserlock.gui.pages import overview
```

### class `OverviewPage(hub, settings, main=None)`

- `on_devices_changed(self)`
- `on_poll(self, role, d)`

## `laserlock.gui.plots`

Plot widget used everywhere in the GUI.

```python
from laserlock.gui import plots
```

### class `BenchPlot(height: int = 170, ylabel: str = '', xlabel: str = '', title: str = '')`

- `set_labels(self, ylabel: str = '', xlabel: str = '') -> None`
- `wheelEvent(self, ev)`
- `save_png(self, path: Optional[str] = None) -> Optional[str]`
- `save_csv(self, path: Optional[str] = None) -> Optional[str]`

### class `BenchViewBox(parent=None, border=None, lockAspect=False, enableMouse=True, invertY=False, enableMenu=True, name=None, invertX=False, defaultPadding=0.02)`

Wheel and drag only act with Ctrl held; double-click re-enables auto-range.

- `wheelEvent(self, ev, axis=None)`
- `mouseDragEvent(self, ev, axis=None)`
- `mouseDoubleClickEvent(self, ev)`
- `raiseContextMenu(self, ev)`

## `laserlock.gui.reference_panel`

Overview panel: which instruments use the 10 MHz (GPS) reference, and whether it is on.

```python
from laserlock.gui import reference_panel
```

**Constants:** `MODE_TEXT`

### class `ReferencePanel(hub, settings, main=None)`

- `rebuild(self)`
- `saved(self, role)` — The reference you chose for this role (True / False), or None if you never set it here.
- `apply_saved(self, role, opt)` — On connect: select the chosen reference the way unticking and re-ticking does (internal, then external), because some instruments report external after power-up but only lock once it is re-selected.
- `set_ref(self, role, opt, on)`
- `on_poll(self, role, d)`

### `reference_state(hub) -> Dict[str, Any]`

{role: {input, mode, in_use}} for every declared reference user (used in data-file headers).

## `laserlock.gui.theme`

Dark instrument theme (matches the mockups).

```python
from laserlock.gui import theme
```

**Constants:** `BAD`, `BAD_BG`, `BG`, `BLUE`, `BLUE_BTN`, `CHROME`, `DIM`, `FONT_MONO`, `FONT_SANS`, `IDLE`, `IDLE_BG`, `INPUT`, `LINE`, `LINE2`, `MUTED`, `OK`, `OK_BG`, `PANEL`, `PILL`, `PLOT1`, `PLOT2`, `PLOT3`, `TEXT`, `WARN`, `WARN_BG`

## `laserlock.gui.widgets`

Small reusable widgets + helpers that persist field values to the settings file.

```python
from laserlock.gui import widgets
```

**Constants:** `CONFIRM`

### class `DiffDialog(parent, title: str, intro: str, rows: List[Tuple], ok_text: str = Write checked)`

Rows (key, live, saved [, note]) with a checkbox each. ``selected()`` → keys.

- `selected(self) -> List[str]`

### class `EngEdit(value: float = 0.0, unit: str = '')`

Number entry that accepts SI suffixes (20n, 1.5u, 2e-6) and shows engineering notation.

- `value(self) -> float`
- `setValue(self, v: float)`

### class `History(maxlen: int = 3600)`

Rolling time series for trend plots.

- `add(self, **vals)`
- `series(self, key: str)`

### class `LogView(max_lines: int = 2000)`

- `add(self, tag: str, msg: str)`

### class `NumEdit(value: float = 0.0, unit: str = '')`

Plain number entry (no SI prefix on display) for dB, ratios, counts … Shows up to 7 significant digits.

- `setValue(self, v: float)`

### class `Panel(title: str = '', right: Optional[QWidget] = None)`

Rounded card with a title row; add widgets to ``.body``.

- `add(self, w)`
- `set_title(self, text: str)`
- `add_right(self, w: QWidget)`

### class `Pill(text: str = '', state: str = idle)`

- `set(self, text: str, state: str = idle)`

### class `Readout(caption: str, value: str = '—', big: bool = False, unit: str = '')`

Caption over a monospaced value.

- `set_si(self, value: Any, unit: Optional[str] = None, digits: int = 6, color: Optional[str] = None)` — Value in SI notation with a prefix (12.5 MHz, 340 µW, 2.1 ns).
- `set(self, value: Any, fmt: str = '{}', color: Optional[str] = None)` — ``fmt`` is a format string, or ``"si:<unit>[:<scale>[:<digits>]]"`` for SI notation (value × scale shown with a prefix, e.g. "si:Hz:1e6" for a value given in MHz).

### class `Seg(options: Sequence[str], current: int = 0)`

Segmented button group. ``changed`` emits the selected index.

- `index(self) -> int`
- `set_index(self, i: int, emit: bool = False)`

### class `StepRow(num: int, title: str)`

- `set(self, status: str, detail: str = '')`

### `bind(settings, key: str, w: QWidget, default: Any = None) -> QWidget`

Load the saved value into ``w`` and save every change (autosaved settings file).

### `button(text: str, kind: str = '', slot: Optional[Callable] = None, tip: str = '') -> QPushButton`

### `combo(items: Iterable, current: Any = None) -> QComboBox`

### `confirm(parent, title: str, text: str, ok_text: str = Continue, danger: bool = False) -> bool`

Yes/no question. Returns True straight away when confirmations are switched off.

### `confirm_checks(parent, title: str, text: str, checks: Sequence[str], ok_text: str = Turn on) -> bool`

Confirmation that needs every checkbox ticked. Skipped when confirmations are off.

### `dspin(value: float = 0.0, lo: float = -1000000000000.0, hi: float = 1000000000000.0, decimals: int = 4, step: float = 0.1, suffix: str = '') -> QDoubleSpinBox`

### `field(caption: str, widget: QWidget) -> QWidget`

### `fmt_num(v, f: str = '{:.4f}') -> str`

### `grid(items: Sequence[QWidget], cols: int = 3, spacing: int = 10) -> QGridLayout`

### `hbox(*items, stretch_end: bool = False, spacing: int = 8) -> QHBoxLayout`

### `ispin(value: int = 0, lo: int = 0, hi: int = 1000000000, suffix: str = '') -> QSpinBox`

### `label(text: str = '', kind: str = lbl, wrap: bool = False) -> QLabel`

### `mark_changed(w: QWidget, changed: bool) -> None`

### `notice(parent, title: str, text: str) -> None`

Information the user asked for (always shown).

### `pen(color: str, width: float = 1.5, dash: bool = False)`

### `plot(height: int = 170, ylabel: str = '', xlabel: str = '', title: str = '')`

Bench plot: auto-range, Ctrl+wheel zoom, SI-prefixed axes for SI units, right-click export.

### `scroll(widget: QWidget) -> QScrollArea`

### `set_combo_data(c: QComboBox, value: Any) -> None`

### `set_row(t: QTableWidget, r: int, values: Sequence[Any], colors: Optional[Dict[int, str]] = None)`

### `table(headers: Sequence[str], rows: int = 0, stretch_last: bool = True) -> QTableWidget`

### `vbox(*items, spacing: int = 10, margins=(0, 0, 0, 0)) -> QVBoxLayout`

## `laserlock.gui.windows.base`

Base for separate instrument windows (scopes, analyzers, generators, meter, SuperK).

```python
from laserlock.gui.windows import base
```

### class `InstrumentWindow(hub, settings, main=None)`

- `make_toolbar(self, items=())` — Top bar: buttons (text, kind, slot) or widgets, then a connection pill + address.
- `make_body(self, margins=(16, 14, 16, 16))`
- `add_tabs(self, main, setup_intro: str = '', extra=())` — Main controls in a "Control" tab and every driver option in a "Setup" tab.
- `connected` *(property)*
- `data_path(self, stem: str, ext: str = csv) -> str`
- `save_columns(self, stem: str, header, columns, ask: bool = True, meta=None)` — CSV with the bench-state header (see laserlock.datafile).
- `on_poll(self, d)`
- `on_devices_changed(self)`
- `call(self, fn, on_done=None, log=None)`
- `closeEvent(self, e)`
- `showEvent(self, e)`

## `laserlock.gui.worker`

One worker thread per device: a job queue plus a ~1 Hz poll.

```python
from laserlock.gui import worker
```

### class `DeviceWorker(role: str, device: Any, poll_s: float = 1.0, reopen: Optional[Callable[[], Any]] = None, on_reopen: Optional[Callable[[Any], None]] = None)`

- `call(self, fn: Callable[[Any], Any], on_done: Optional[Callable[[Any], None]] = None, on_error: Optional[Callable[[Exception], None]] = None) -> None`
- `stop(self, safe: bool = True, timeout: float = 5.0, wait: bool = True) -> threading.Event` — Close the device in its own thread. Pending jobs are dropped first, so a backlog (or one slow call) doesn't hold up closing. ``wait=False`` returns at once with an Event set when it's closed.

### class `Hub(settings)`

All workers, the event log and the poll logger.

- `attach(self, role: str, device: Any, found=None, poll_s: float = 1.0, reopen=None, on_reopen=None) -> DeviceWorker`
- `detach(self, role: str, safe: bool = True, wait: bool = True)` — Stop the role's worker. With ``wait=False`` the window never blocks: the returned Event is set once the instrument is closed.
- `close_all(self, safe: bool = True, timeout: float = 2.0)` — Close every instrument in parallel and wait at most ``timeout`` seconds in total (worker threads are daemons, so one stuck on a slow port can't stop the app from exiting).
- `has(self, role: str) -> bool`
- `device(self, role: str)`
- `call(self, role: str, fn, on_done=None, on_error=None, log: Optional[str] = None)`
- `last(self, role: str) -> Dict[str, Any]`
- `emit_log(self, tag: str, msg: str)`
- `start_logging(self, folder: str)`
- `stop_logging(self)`

## `laserlock.settings`

Auto-saved settings file.

```python
from laserlock import settings
```

**Constants:** `APP_NAME`, `SCHEMA_VERSION`

### class `Settings(path: Optional[os.PathLike] = None, autosave_delay: float = 1.0, autosave: bool = True)`

Dotted-key settings store with debounced atomic autosave.

- `load(self) -> None`
- `save(self) -> Path` — Write now (atomic). Returns the path written.
- `flush(self) -> None` — Save if anything changed since the last write.
- `get(self, key: str, default: Any = None) -> Any`
- `set(self, key: str, value: Any) -> None`
- `update(self, key: str, values: Dict[str, Any]) -> None`
- `delete(self, key: str) -> None`
- `on_change(self, cb: Callable[[str, Any], None]) -> None`
- `role(self, role: str) -> Dict[str, Any]`
- `set_role(self, role: str, kind: str, serial: str, model: str = '', address: str = '') -> None`
- `save_device_state(self, role: str, snapshot: Dict[str, Any]) -> None`
- `device_state(self, role: str) -> Dict[str, Any]`

### `default_data_dir() -> Path`

Where recordings, scans and captures go unless the user picks a folder.

### `default_settings_path() -> Path`

## `laserlock.sim.base`

Building blocks for simulated instruments (used by every add-on's ``sim.py``).

```python
from laserlock.sim import base
```

### class `OptionStore(defaults=None)`

Remembers ``HEADER value`` writes and answers ``HEADER?`` with them.

- static `key(header: str) -> str`
- `get(self, header, default=None)`
- `set(self, header, value)`
- `handle(self, cmd: str)`

### class `SCPIModel()`

Base for VISA models: ``handle(cmd) -> reply | None`` (bytes for binary blocks).

- `handle(self, cmd: str)`
- `binary(self, cmd)`

### class `SilentModel()`

A GPIB address that never answers (exercises the 'unknown' path).

### `null_generator()`

### `num(s: str) -> float`

First number in a command argument ('500MV' -> 500.0, '2.5E-6S' -> 2.5e-06).

## `laserlock.sim.fakeio`

Byte-level fake serial port and fake VISA resource manager.

```python
from laserlock.sim import fakeio
```

### class `FakeResource(name: str, model)`

- `write(self, cmd: str)`
- `read(self) -> str`
- `query(self, cmd: str) -> str`
- `read_raw(self) -> bytes`
- `read_stb(self) -> int`
- `query_binary_values(self, cmd, datatype=B, is_big_endian=False, container=<class list>, **kw)`
- `clear(self)`
- `close(self)`

### class `FakeResourceManager(models: Dict[str, object])`

- `list_resources(self, query: str = '?*::INSTR')`
- `open_resource(self, name: str, **kw)`
- `close(self)`

### class `FakeSerial(port: str, handler: Callable[[bytes], bytes], terminator: bytes = b'\r', baudrate: int = 115200, timeout: float = 1.0, expected_baud: Optional[int] = None, serial_number: str = '', strip_lf: bool = True)`

Implements the subset of pyserial the drivers use.

- `in_waiting` *(property)*
- `write(self, data: bytes) -> int`
- `read(self, n: int = 1) -> bytes`
- `read_until(self, expected: bytes = b'\n', size: Optional[int] = None) -> bytes`
- `flush(self)`
- `reset_input_buffer(self)`
- `reset_output_buffer(self)`
- `close(self)`

### class `TextDevice()`

Base for ASCII command/response simulators.

- `handle(self, cmd: str) -> Optional[str]`

### `visa_timeout()`

## `laserlock.sim.world`

The simulated bench. The shell provides an empty world; each add-on's ``sim.py`` fills it.

```python
from laserlock.sim import world
```

### class `World(speed: float = 1.0, cavity_tau_s: float = 3.0)`

- `add_serial(self, info: PortInfo, handler, terminator: bytes = b'\r', expected_baud: int = 115200, strip_lf: bool = True) -> None`
- `add_visa(self, resource: str, model) -> None`
- `add_rf_line(self, fn: Callable[[], List[Tuple[float, float]]]) -> None`
- `on_uninstall(self, fn: Callable[[], None]) -> None`
- `rf_lines(self) -> List[Tuple[float, float]]`
- `beat_offset_hz(self, opl) -> float`
- `beat_phase_rms(self) -> float`
- `pzt_out(self) -> float`
- `ports(self) -> List[PortInfo]`
- `serial_factory(self, port: str, baudrate: int = 115200, timeout: float = 1.0)`

### `get_world() -> Optional[World]`

### `install(speed: float = 1.0, cavity_tau_s: float = 3.0, settings=None) -> World`

Route discovery and drivers to a simulated bench built by the loaded add-ons.

### `uninstall() -> None`

## `laserlock_addons.laser_lock`

Laser lock module — tunable laser, SLICE-OPL #2 (Brimrose AOM), Rigol MHO5104 (beat monitor), Laser lock page.

```python
from laserlock_addons import laser_lock
```

**Constants:** `SECTION`

### `register(api)`

## `laserlock_addons.laser_lock.autotune`

Auto-tune an OPL servo filter.

```python
from laserlock_addons.laser_lock import autotune
```

**Constants:** `METRICS`, `NEEDS`, `SCOPE_METRICS`, `SCOPE_USER`

### class `AutoTuner(opl, cfg: TuneConfig, scope=None, sa=None, on_trial: Optional[Callable[[Trial, int, int], None]] = None, on_log: Optional[Callable[[str], None]] = None)`

- `start_thread(self)`
- `stop(self)`
- `estimate_trials(self) -> int`
- `revert(self)`
- `locked(self) -> bool`
- `measure_scope(self) -> Dict[str, float]` — ≥ 3 captures: integrated phase (rad), median FWHM (Hz), movement = std of the peak (Hz).
- `measure(self) -> float` — Score for the chosen metric; scope metrics also fill ``self.last_extra``.
- `run(self) -> Optional[Trial]`
- `apply_best(self)`

### class `Trial(gain_db: float, int_hz: float, diff_hz: Optional[float], clamp: Optional[bool], score: float, locked: bool, extra: Dict[str, float] = <factory>) -> None`

- `as_dict(self)`

### class `TuneConfig(metric: str = phase_scope, gains_db: List[float] = <factory>, int_corners_hz: List[float] = <factory>, diff_corners_hz: Optional[List[float]] = None, gain_clamp: Optional[List[bool]] = None, strategy: str = coordinate, dwell_s: float = 5.0, averages: int = 4, max_trials: int = 60, max_gain_step_db: float = 2.0, revert_on_loss: bool = True, scope_channel: int = 2, scope_span_hz: float = 2000000.0, band_hz: tuple = (10.0, 1000000.0)) -> None`

- `as_dict(self)`
- class `from_dict(cls, d)`

## `laserlock_addons.laser_lock.beat_check`

When an OPL counter shows no beat, look for it with the spectrum analyzer or scope.

```python
from laserlock_addons.laser_lock import beat_check
```

### class `BeatCheckConfig(source: str = scope, center_hz: Optional[float] = None, span_hz: float = 20000000.0, rbw_hz: float = 100000.0, min_dbm: float = -60.0, scope_channel: int = 2, every_s: float = 10.0, offer_retarget: bool = False) -> None`

- `as_dict(self)`
- class `from_dict(cls, d)`

### class `BeatResult(found: bool, source: str = '', freq_hz: float = nan, level_dbm: float = nan, target_hz: float = nan, note: str = '', trace_f: Any = None, trace_p: Any = None) -> None`

- `offset_hz` *(property)*

### `beat_fwhm(t: np.ndarray, v: np.ndarray, center_hz: float, span_hz: float = 2000000.0, trace: bool = False) -> Dict[str, Any]`

FWHM of the beat in a scope record (Hann FFT, half power = −3 dB, linear interpolation).

### `check_with_sa(sa, center_hz: float, cfg: BeatCheckConfig, name: str = spectrum analyzer) -> BeatResult`

### `check_with_scope(scope, center_hz: float, cfg: BeatCheckConfig, name: str = scope FFT) -> BeatResult`

### `measure_beat(scope, channel: int, center_hz: float, span_hz: float = 2000000.0, trace: bool = False) -> Dict[str, Any]`

One scope capture → beat FWHM / peak (the scope only watches; nothing is changed).

### `measure_beat_any(dev, center_hz: float, span_hz: float, channel: int = 2, trace: bool = False)`

Scope (time record → FFT) or spectrum analyzer: same result fields either way.

### `measure_beat_sa(sa, center_hz: float, span_hz: float = 2000000.0, trace: bool = False) -> Dict[str, Any]`

One analyzer sweep around the target → beat FWHM / peak. Centre and span are set only when they differ (nothing else on the analyzer is changed); the RBW is the analyzer's own (coupled unless you set it).

### `spectrum_fwhm(f, p_dbm, center_hz: float, span_hz: float, rbw_hz: Optional[float] = None, trace: bool = False) -> Dict[str, Any]`

Beat peak and −3 dB width from an analyzer trace (dBm). The width can't be narrower than the RBW: a FWHM ≈ rbw_hz means the line is narrower than the analyzer resolves.

### `verify_beat(opl, sa=None, scope=None, cfg: Optional[BeatCheckConfig] = None, sa_name: str = spectrum analyzer, scope_name: str = scope FFT) -> BeatResult`

Counter first; if it shows nothing, ask the analyzer (or scope).

## `laserlock_addons.laser_lock.comb_link`

Comb state from the Vescent Comb application.

```python
from laserlock_addons.laser_lock import comb_link
```

**Constants:** `STALE_S`

### `comb_locked(settings=None, require: bool = True) -> Tuple[bool, str]`

For the laser lock sequence: (ok, note). ``require=False`` lets a missing comb app pass.

### `default_path() -> Path`

### `fceo_hz(settings=None) -> Optional[float]`

### `read_status(settings=None) -> Dict[str, Any]`

The last comb status, plus ``age_s`` and ``ok_file``. ``{}``-like dict when missing.

### `status_path(settings=None) -> Path`

### `verdict(st: Dict[str, Any]) -> Tuple[str, str]`

(text, kind) for a pill: ok / warn / bad / idle.

## `laserlock_addons.laser_lock.comb_tooth`

Which comb tooth is the laser next to?  ν_n = n·f_rep + f_ceo.

```python
from laserlock_addons.laser_lock import comb_tooth
```

**Constants:** `C`

### class `Tooth(n: int, nu_n_hz: float, lambda_n_nm: float, offset_hz: float, expected_beat_hz: float, n_uncertainty: Optional[int], side: str, measured_beat_hz: Optional[float] = None, laser_hz_if_above: Optional[float] = None, laser_hz_if_below: Optional[float] = None) -> None`


### `laser_sigma_hz(nu_hz: float, accuracy_nm: float) -> float`

Frequency uncertainty of a wavelength readback with ±``accuracy_nm`` absolute accuracy.

### `nearest_tooth(nu_hz: float, frep_hz: float, fceo_hz: float = 0.0, sigma_nu_hz: Optional[float] = None, measured_beat_hz: Optional[float] = None) -> Tooth`

## `laserlock_addons.laser_lock.hp8168`

HP / Agilent 8168D and 8168E tunable laser sources (GPIB, SCPI-like).

```python
from laserlock_addons.laser_lock import hp8168
```

**Constants:** `GRID_CHOICES_NM`, `MAX_POWER_W`, `MODEL_SPECS`

### class `HP8168(resource: Optional[str] = None, model: Optional[str] = None, inst=None, timeout_ms: int = 15000)`

- `close(self) -> None`
- `safe_state(self) -> None`
- `check_errors(self)`
- `identify(self) -> Identity`
- `reset(self)`
- `clear(self)`
- `self_test(self)`
- `status(self) -> Dict[str, Any]`
- `snap(self, wl_nm: float) -> float`
- `set_wavelength_nm(self, wl_nm: float) -> Optional[float]`
- `set_wavelength(self, wl_nm: float) -> Optional[float]`
- `get_wavelength_nm(self) -> Optional[float]`
- `set_frequency_thz(self, thz: float)`
- `step(self, n_steps: int = 1)`
- `set_power_w(self, watts: float) -> Optional[float]`
- `set_power_dbm(self, dbm: float)`
- `set_power_uw(self, uw: float)`
- `get_power_w(self) -> Optional[float]`
- `output_on(self, confirm: bool = True) -> None` — Laser current on. (``confirm`` is accepted for older scripts and ignored.)
- `output_off(self) -> None`
- `output_is_on(self) -> Optional[bool]`
- `set_am_source(self, code: int)`
- `get_am_source(self)`
- `set_am_state(self, on: bool)`
- `get_am_state(self) -> Optional[bool]`
- `set_am_frequency(self, hz: float)`
- `get_am_frequency(self)`
- `set_coherence_control(self, on: bool)`
- `stepped_sweep(self, start_nm, stop_nm, step_nm, dwell_s=0.5, callback=None, stop_event=None, confirm: bool = True)` — Software step + dwell. Output on at start, always off at the end.
- `poll(self) -> Dict[str, Any]`
- `snapshot(self) -> Dict[str, Any]`

## `laserlock_addons.laser_lock.hp8563e`

HP / Agilent 8563E spectrum analyzer (GPIB, HP proprietary commands).

```python
from laserlock_addons.laser_lock import hp8563e
```

**Constants:** `POINTS`

### class `HP8563E(resource: Optional[str] = None, inst=None, timeout_ms: int = 30000, sweep_timeout_s: float = 120)`

- `close(self) -> None`
- `w(self, cmd)`
- `qf(self, cmd) -> Optional[float]`
- `identify(self) -> Identity`
- `reset(self)`
- `write_option(self, key, value=None, readback=True)`
- `clear(self)`
- `configure(self, center_hz=None, span_hz=None, ref_dbm=None, rbw_hz=None, vbw_hz=None, atten_db=None, sweep_time_s=None) -> None`
- `set_center_hz(self, f)`
- `set_span_hz(self, f)`
- `set_start_stop(self, a, b)`
- `set_ref_dbm(self, d)`
- `set_rbw_hz(self, f)`
- `set_vbw_hz(self, f)`
- `set_detector(self, mode=POS)`
- `set_trace_mode(self, mode=CLRW, trace=TRA)`
- `set_averaging(self, count=10, enable=True)`
- `set_scale(self, scale: str = log, db_per_div: float = 10) -> None` — 'log' → LG n dB/div with dBm; 'lin' → LN with watts (traces then come back in W).
- `get_scale(self) -> Optional[str]`
- `amplitude_unit(self) -> str`
- `set_ext_ref(self, on: bool) -> None`
- `ext_ref(self) -> Optional[bool]`
- `settings(self) -> Dict[str, Optional[float]]`
- `single_sweep(self) -> bool`
- `continuous(self)`
- `fetch_trace(self, trace: str = TRA) -> Tuple[np.ndarray, np.ndarray]`
- `sweep_and_fetch(self, trace: str = TRA)`
- `peak_search(self) -> Tuple[Optional[float], Optional[float]]`
- `next_peak(self)`
- `marker_at(self, f_hz: float) -> Optional[float]`
- `markers_off(self)`
- `stitched_sweep(self, start_hz: float, stop_hz: float, resolution_hz: Optional[float] = None, total_points: Optional[int] = None, rbw_hz=None, vbw_hz=None, stop_event=None, progress=None) -> Dict[str, np.ndarray]`
- `poll(self) -> Dict[str, Any]`
- `snapshot(self) -> Dict[str, Any]`

## `laserlock_addons.laser_lock.hp8563e_sim`

Simulated HP 8563E for Laser Lock: shows the laser↔comb beat (narrow when OPL #2 is locked).

```python
from laserlock_addons.laser_lock import hp8563e_sim
```

### class `HP8563EModel(world)`

- `handle(self, c)`

### `install(world) -> None`

## `laserlock_addons.laser_lock.laser_sequence`

Laser lock sequence: put the tunable laser on the comb with SLICE-OPL #2 (Brimrose AOM).

```python
from laserlock_addons.laser_lock import laser_sequence
```

**Constants:** `SCOPE_USER`, `STEP_IDS`, `STEP_TITLES`

### class `Aborted(…)`

### class `LaserLockParams(wavelength_nm: Optional[float] = None, power_uw: Optional[float] = None, require_comb: bool = True, pll_min_v: float = 7.0, pll_max_v: float = 12.0, enforce_limits: bool = True, rail_margin: float = 0.05, rail_relocks: int = 2, break_wait_s: float = 0.5, setpoint_check: bool = True, window_hz: float = 200.0, dwell_s: float = 5.0, poll_s: float = 0.5, servo_wait_s: float = 2.0, scope_channel: int = 2, beat_role: str = scope, scope_span_hz: float = 70000000.0, beat_near_hz: float = 10000000.0, beat_still_hz: float = 10000000.0, beat_still_s: float = 30.0, beat_timeout_s: float = 600.0, beat_every_s: float = 1.0, scope_every_s: float = 1.0, max_fwhm_hz: float = 0.0, dry_run: bool = False) -> None`

- `as_dict(self)`
- class `from_dict(cls, d)`

### class `LaserLockSequence(devices: Dict[str, Any], params: Optional[LaserLockParams] = None, on_step=None, on_log=None, on_sample=None, ask=None, comb_status: Optional[Callable[[], Any]] = None)`

``devices``: laser, opl2 (required), scope (optional: monitor only). ``comb_status() -> (ok, note)`` reports the comb lock (default: the Vescent Comb app's status file).

- `start(self)`
- `stop(self)`
- `pause(self, on: bool = True)`
- `run(self) -> bool`
- `pll_railed(self, out, lo, hi) -> Optional[bool]` — True if the PLL output sits within ``rail_margin`` of PLLMIN/PLLMAX (None if unreadable).

### class `StepState(id: str, title: str, status: str = wait, detail: str = '') -> None`


## `laserlock_addons.laser_lock.laser_setpoints`

Laser wavelength / power working range for the comb lock, and "fields follow the laser".

```python
from laserlock_addons.laser_lock import laser_setpoints
```

**Constants:** `HOLD_S`, `POWER_DEFAULT_W`, `POWER_RANGE_W`, `WL_DEFAULT_NM`, `WL_RANGE_NM`

### class `FieldPull(*widgets: Any)`

Decides when the entry fields may be refreshed from the laser.

- `clear(self) -> None` — After Set: follow the laser again straight away.
- `free(self) -> bool`

### `apply(laser, changes: Dict[str, Tuple[float, float]]) -> None`

### `check(wl_nm: Optional[float], power_w: Optional[float]) -> Dict[str, Tuple[float, float]]`

{"wavelength_nm": (now, proposed), "power_w": (now, proposed)} for whatever is out of range.

### `describe(changes: Dict[str, Tuple[float, float]]) -> str`

## `laserlock_addons.laser_lock.opl_sim`

Simulated SLICE-OPL (OPL #2).

```python
from laserlock_addons.laser_lock import opl_sim
```

### class `OPLModel(world, serial: str, target_mhz: float, has_beat: bool = True, pll=(0.0, 10.0, 5.0))`

- `true_beat_hz(self) -> float`
- `servo_quality(self)` — Lock lost above about -43 dB gain (used by the auto-tune simulation).
- `update_lock(self)` — Like the bench: once the servo is on without a lock the integrator rails, and it stays railed (won't capture even if the beat comes within range) until the servo is switched off.
- `handle(self, cmd: str) -> Optional[str]`

## `laserlock_addons.laser_lock.overview`

Laser-lock cards for the Overview page.

```python
from laserlock_addons.laser_lock import overview
```

### class `LaserCard(hub, settings, main=None)`

- `transform(self, d)`

### class `OPL2Card(hub, settings, main=None)`

- `transform(self, d)`

## `laserlock_addons.laser_lock.pages.beat_monitor`

Scope beat monitor — the same panel on the Laser lock and OPL #2 pages (no separate scope window).

```python
from laserlock_addons.laser_lock.pages import beat_monitor
```

**Constants:** `DEFAULT_SPAN_HZ`, `KEY`, `SCOPE_USER`, `WAVE_POINTS`

### class `BeatMonitor(hub, settings, parent=None, title: str = 'Beat monitor · scope')`

- `capture(self, quiet: bool = False)`
- `show_result(self, r: dict)`

### `channel(settings) -> int`

### `source(settings) -> str`

The beat instrument: "scope" (Rigol, FFT of CH2) or "sa" (HP 8563E spectrum analyzer).

### `span_hz(settings) -> float`

## `laserlock_addons.laser_lock.pages.laser`

Tunable laser page — one page, model chosen from a dropdown of what the scan found.

```python
from laserlock_addons.laser_lock.pages import laser
```

**Constants:** `C_LIGHT`, `GRID_CHOICES_NM`, `MODELS`, `MODEL_SPECS`

### class `LaserPage(hub, settings, main=None)`

- `grid_nm` *(property)*
- `on_devices_changed(self)`
- `choose_model(self, i)`
- `set_grid(self, i)`
- `on_poll(self, role, d)`
- `output_on(self)`
- `output_off(self)`
- `set_wl(self)`
- `step(self, n)`
- `set_power(self)`
- `run_scan(self)`
- `stop_scan(self)`

## `laserlock_addons.laser_lock.pages.opl`

SLICE-OPL page. The comb lock module uses it for OPL #1; other modules subclass it (``OPL2Page`` in laser_lock adds the beat-check tab and the Brimrose limits note).

```python
from laserlock_addons.laser_lock.pages import opl
```

**Constants:** `INTEGRATOR_CORNERS_HZ`, `METRICS`, `NEEDS`, `SCOPE_METRICS`

### class `OPLPage(hub, settings, main=None, role: str = None)`

- `extra_tabs(self)` — Subclasses return [(QWidget, label), …] to insert after the first tab.
- `on_devices_changed(self)`
- `on_scope_owner(self)` — Scope metrics are off while the Rigol window is open (and vice versa).
- `choose_unit(self, i)`
- `identify(self)`
- `reread(self)`
- `read_adcs(self)`
- `on_poll(self, role, d)`
- `set_servo(self, i)`
- `set_target(self)`
- `apply_filter(self)`
- `apply_ref(self)`
- `apply_beatin(self)`
- `apply_aux(self)`
- `apply_sweep(self)`
- `apply_io(self)`
- `reboot(self)`
- `send_raw(self)`
- `start_tune(self)`
- `stop_tune(self)`

## `laserlock_addons.laser_lock.pages.opl2`

SLICE-OPL #2 (laser → comb, drives the Brimrose AOM): the comb module's OPL page plus a beat check.

```python
from laserlock_addons.laser_lock.pages import opl2
```

**Constants:** `SCOPE_USER`

### class `OPL2Page(hub, settings, main=None, role: str = None)`

- `extra_tabs(self)`
- `on_scope_owner(self)`
- `on_devices_changed(self)`
- `beat_check_now(self)`

### `beat_config(settings, role_key: str = ui.opl2.beatcheck) -> BeatCheckConfig`

### `beat_instruments(hub)`

[(label, role, kind)] of every installed analyzer / scope add-on, connected or not.

### `run_beat_check(hub, settings, opl)`

Counter first, then the chosen analyzer/scope (or any connected one). Blocking.

## `laserlock_addons.laser_lock.pages.process`

Laser lock — one page with everything the laser→comb lock needs: laser, OPL #2, comb state, the scope beat monitor (same panel as on the OPL #2 page), the lock steps and the trends.

```python
from laserlock_addons.laser_lock.pages import process
```

**Constants:** `C_LIGHT`, `STEP_IDS`, `STEP_TITLES`

### class `LaserLockPage(hub, settings, main=None)`

- `on_devices_changed(self)`
- `on_poll(self, role, d)`
- `set_wl(self)`
- `set_pw(self)`
- `laser_on(self)`
- `laser_off(self)`
- `set_target(self)`
- `set_servo(self, i)`
- `beat_check(self)`
- `start(self, from_watchdog: bool = False)`
- `stop(self)`

### `pll_railed(d, margin=0.05)`

True / False from an OPL poll dict (None if the voltages aren't there).

## `laserlock_addons.laser_lock.rigol_mho5104`

Rigol MHO5104 oscilloscope (USB-TMC, SCPI).

```python
from laserlock_addons.laser_lock import rigol_mho5104
```

**Constants:** `AVERAGES`, `MAX_SAMPLE_RATE`, `MEAS_INVALID`, `MEAS_ITEMS`, `MEMORY_DEPTHS`, `SCREEN_DIVISIONS`, `SECONDS_PER_DIV`, `VISA_CHUNK`, `VOLTS_PER_DIV`

### class `RigolMHO5104(resource: Optional[str] = None, inst=None, timeout_ms: int = 5000)`

- `close(self) -> None`
- `recover(self) -> None`
- `w(self, cmd: str, quiet: bool = False) -> Optional[str]`
- `q(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[str]`
- `option_write(self, cmd: str) -> None`
- `qf(self, cmd: str, timeout_ms: Optional[int] = None) -> Optional[float]`
- `option_query(self, cmd: str) -> Optional[str]`
- `check_errors(self) -> List[str]`
- `identify(self) -> Identity`
- `reset(self)`
- `run(self)`
- `stop(self)`
- `single(self)`
- `autoscale(self)` — MHO5000: :AUToset (:AUToscale is not defined on this series).
- `clear_display(self)`
- `force_trigger(self)`
- `trigger_status(self) -> Optional[str]`
- `status(self) -> Dict[str, Any]`
- `wait_trigger(self, timeout_s: float = 10) -> Optional[str]`
- `arm_and_wait(self, timeout_s: float = 20) -> bool` — :SINGle, then require the status to LEAVE stop before waiting for it.
- `set_timebase(self, scale_s: float, offset_s: float = 0.0, mode: str = MAIN) -> None`
- `set_timebase_scale(self, scale_s)`
- `set_timebase_offset(self, off_s)`
- `get_timebase(self) -> Dict[str, Any]`
- `channel_display(self, n: int, on: bool) -> None`
- `set_channel(self, n: int, scale_v: Optional[float] = None, offset_v: Optional[float] = None, coupling: Optional[str] = None, bwlimit: Optional[str] = None, probe: Optional[float] = None, impedance: Optional[str] = None, unit: Optional[str] = None, invert: Optional[bool] = None, display: Optional[bool] = None) -> None`
- `get_channel(self, n: int) -> Dict[str, Any]`
- `get_all_channels(self) -> Dict[int, Dict[str, Any]]`
- `set_acquire(self, acq_type: str = NORM, averages: int = 4, mdepth: Optional[int] = None) -> None`
- `set_acquire_type(self, t)`
- `set_memory_depth(self, n)`
- `get_acquire(self) -> Dict[str, Any]`
- `set_trigger_edge(self, source=CHAN1, slope=POS, level_v=0.0, sweep=AUTO, coupling=DC, holdoff_s=8e-09) -> None`
- `set_trigger_pulse(self, source=CHAN1, when=GRE, width_s=1e-06, level_v=0.0, sweep=AUTO)`
- `get_trigger(self) -> Dict[str, Any]`
- `measure(self, item: str, channel: int = 1) -> float`
- `measure_all(self, channel: int = 1, items: Optional[Iterable[str]] = None) -> Dict[str, float]`
- `read_preamble(self) -> Dict[str, Any]`
- `screen_capture(self, channels: Iterable[int]) -> Dict[int, Tuple[np.ndarray, np.ndarray]]` — What the screen shows right now (:WAVeform:MODE NORMal, BYTE): small, quick, and the scope keeps running. Returns {channel: (t_s, v_V)}.
- `capture(self, channel: int = 1, max_points: Optional[int] = None)` — Generic "scope" capability: CH<n> -> (t_s, v_V); leaves the scope running. At most ``max_points`` (1 M by default) so a deep memory setting can't stall the link.
- `capture_waveform(self, channel: int = 1, points: Optional[int] = None, fmt: str = WORD, chunk_points: int = 1000000, resume: bool = False) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]` — Read CH<n> from deep memory. Returns (t_s, v_V, preamble).
- `capture_channels(self, channels: Iterable[int], points: Optional[int] = None, fmt: str = WORD) -> Dict[str, np.ndarray]` — Capture several channels from ONE stopped acquisition (shared time axis).
- `save_waveform(self, path: str, channels: Iterable[int] = (1,), points: Optional[int] = None, fmt: str = WORD) -> str`
- `screenshot_bytes(self) -> bytes` — Returns PNG bytes (BMP if Pillow is missing).
- `screenshot(self, path: str) -> str`
- `set_math(self, math_n=1, operator=ADD, source1=CHAN1, source2=CHAN2, scale=1.0, offset=0.0, display=True, fft_center_hz=None, fft_window=HANN, fft_unit=DB)`
- `set_math_fft_center(self, math_n: int, center_hz: float)`
- `set_math_fft_span(self, span_hz: float, mdepth: Optional[int] = None) -> Dict[str, float]` — FFT span = MDEPth / (timebase × 20); sets the timebase to get it.
- `math_display(self, math_n: int, on: bool)`
- `get_math(self, math_n: int) -> Dict[str, Any]`
- `cursor_mode(self, mode: str = MAN)`
- `cursor_item(self)`
- `set_awg_function(self, func: str = SIN)`
- `set_awg_frequency(self, hz: float)`
- `get_awg(self) -> Dict[str, Any]`
- static `plan_nyquist(freq_hz: float, mdepth: int = 100000) -> Dict[str, Any]` — Same arithmetic as scope_setup_for_nyquist() in the notebook.
- `setup_for_nyquist(self, freq_hz: float, channel: int = 1, mdepth: int = 100000, coupling: str = DC, probe: float = 1, trigger_level_v: float = 0.0, trigger_slope: str = POS) -> Dict[str, Any]`
- `set_ext_ref(self, on: bool) -> None` — Rear 10 MHz REF IN on/off (Utility → EXT 10M IN).
- `set_ref_clock(self, mode: str) -> None` — CINP (use the external 10 MHz), COUT (output the internal one) or OFF.
- `ext_ref(self) -> Optional[bool]`
- `autorange_vertical(self, channel: int = 1, fill_divisions: float = 6.0, passes: int = 4, coarse: bool = True) -> Optional[float]` — Adjust V/div so Vpp fills ~6 of 8 divisions (from the monitor notebook).
- `autorange_displayed(self, fill_divisions: float = 6.0) -> Dict[int, Optional[float]]` — Auto V/div on every displayed channel; returns {channel: V/div}.
- `poll(self) -> Dict[str, Any]` — Kept to one query: anything more is read when a window asks for it.
- `snapshot(self) -> Dict[str, Any]`

### `build_options()`

## `laserlock_addons.laser_lock.scope_owner`

Who may use the Rigol right now: the Rigol window, or one OPL #2 / Laser lock feature — never both.

```python
from laserlock_addons.laser_lock import scope_owner
```

**Constants:** `BLOCKED_TEXT`

### `acquire(name: str, wait_s: float = 0.0) -> bool`

Take the scope for a feature. False while the Rigol window is open (or another feature holds it longer than ``wait_s``). The same name may acquire again (counted).

### `blocked_reason(name: str = '') -> str`

'' when ``name`` could take the scope now, otherwise why not.

### `owner() -> Optional[str]`

### `release(name: str) -> None`

### `reset() -> None`

Tests only.

### `set_window_open(on: bool) -> None`

### `subscribe(cb: Callable[[], None]) -> None`

### `unsubscribe(cb: Callable[[], None]) -> None`

### `window_has_scope() -> bool`

The Rigol window is open and no feature is still holding the scope.

### `window_open() -> bool`

## `laserlock_addons.laser_lock.sim`

Simulator for this add-on: models answer the same commands as the real instrument.

```python
from laserlock_addons.laser_lock import sim
```

**Constants:** `C`, `LOCK_WL_NM`

### class `HP8168Model(model=HP8168D, serial='3610G00108')`

- `handle(self, c)`

### class `RigolModel(world)`

- `srate(self)`
- `handle(self, c)`
- `binary(self, cmd)`

### class `SWSModel()`

- `handle(self, c)`

### `install(world) -> None`

OPL #2 on COM11, HP 8168E + SWS17101 on GPIB, Rigol on USB.

## `laserlock_addons.laser_lock.sliceopl`

Vescent SLICE-OPL offset phase lock (USB serial, CR, ASCII).

```python
from laserlock_addons.laser_lock import sliceopl
```

**Constants:** `INTEGRATOR_CORNERS_HZ`, `RAIL_V`

### class `SliceOPL(port: Optional[str] = None, baudrate: int = 115200, timeout: float = 1.0, ser=None)`

- `ser` *(property)*
- `close(self) -> None`
- `query(self, cmd: str) -> str`
- `command(self, cmd: str) -> str`
- `query_value(self, cmd: str) -> str`
- `query_float(self, cmd: str)`
- `query_int(self, cmd: str)`
- `idn(self) -> str`
- `identify(self) -> Identity`
- `reset(self) -> str`
- `get_backlight(self)`
- `set_backlight(self, level)`
- `get_volume(self)`
- `set_volume(self, level)`
- `flash_identify(self, cycles: int = 3, period_s: float = 0.4) -> None` — Blink the front-panel backlight so you can see which box this is.
- `get_servo(self)`
- `servo_on(self) -> bool`
- `set_servo(self, on)`
- `get_target_beatnote(self)`
- `set_target_beatnote(self, mhz)`
- `read_voltage(self, channel)`
- `read_all_voltages(self) -> Dict[str, Any]`
- `get_pll_invert(self)`
- `set_pll_invert(self, on)`
- `get_pll_gain(self)`
- `set_pll_gain(self, db)`
- `get_integrator_corner(self)`
- `set_integrator_corner(self, hz)`
- `get_diff_corner(self)`
- `set_diff_corner(self, hz)`
- `get_gain_clamp(self)`
- `set_gain_clamp(self, on)`
- `get_pll_bias(self)`
- `set_pll_bias(self, volts)`
- `get_pll_max(self)`
- `set_pll_max(self, volts)`
- `get_pll_min(self)`
- `set_pll_min(self, volts)`
- `set_pll_limits(self, vmin: float, vmax: float, bias: Optional[float] = None) -> None` — Set min/max (and optionally bias) in an order that never violates min<max.
- `get_lock_range(self)`
- `set_lock_range(self, volts)`
- `get_aux_enabled(self)`
- `set_aux_enabled(self, on)`
- `get_aux_invert(self)`
- `set_aux_invert(self, on)`
- `get_aux_target(self)`
- `set_aux_target(self, volts)`
- `get_aux_gain(self)`
- `set_aux_gain(self, g)`
- `get_aux_bias(self)`
- `set_aux_bias(self, volts)`
- `get_aux_max(self)`
- `set_aux_max(self, volts)`
- `get_aux_min(self)`
- `set_aux_min(self, volts)`
- `get_ramp(self)`
- `set_ramp(self, on)`
- `get_ramp_channel(self)`
- `set_ramp_channel(self, ch)`
- `get_ramp_points(self)`
- `set_ramp_points(self, n)`
- `get_ramp_freq(self)`
- `set_ramp_freq(self, hz)`
- `get_ramp_range(self)`
- `set_ramp_range(self, volts)`
- `get_ramp_adc_gain(self)`
- `set_ramp_adc_gain(self, mode)`
- `get_bn_max(self)`
- `set_bn_max(self, mhz)`
- `get_n1(self)`
- `set_n1(self, val)`
- `get_n2(self)`
- `set_n2(self, val)`
- `read_beatnote(self)`
- `read_reference(self)`
- `get_ext_ref_bw(self)`
- `set_ext_ref_bw(self, mhz)`
- `get_pfd_uses_dds(self)`
- `set_pfd_uses_dds(self, on)`
- `get_dds_internal(self)`
- `set_dds_internal(self, on)`
- `get_dds_ref_freq(self)`
- `set_dds_ref_freq(self, mhz)`
- `get_m1(self)`
- `set_m1(self, val)`
- `get_m2(self)`
- `set_m2(self, val)`
- `dds_auto(self)`
- `get_rear_mux(self)`
- `set_rear_mux(self, val)`
- `get_front_out1(self)`
- `set_front_out1(self, on)`
- `get_front_out2(self)`
- `set_front_out2(self, on)`
- `get_front_out2_mux(self)`
- `set_front_out2_mux(self, val)`
- `get_front_in_a(self)`
- `set_front_in_a(self, on)`
- `get_front_in_b(self)`
- `set_front_in_b(self, on)`
- `get_trigger_in(self)`
- `set_trigger_in(self, mode)`
- `get_trigger_out(self)`
- `set_trigger_out(self, mode)`
- `integrator_hold(self, on)`
- `get_integrator_hold(self)`
- `disable_cp(self)`
- `get_dds_freq(self)`
- `set_dds_freq(self, mhz)`
- `get_dds_raw(self)`
- `set_dds_raw(self, raw)`
- `beat_error_hz(self, counter_offset_mhz: float = 0.0) -> Optional[float]` — (target - offset - measured) in Hz. Positive = beat is LOW.
- `has_beat(self, min_mhz: float = 1.0) -> bool`
- `poll(self) -> Dict[str, Any]`
- `snapshot(self) -> Dict[str, Any]`
- `safe_state(self) -> None` — Servo state is left alone: dropping a lock on disconnect would be worse.

## `laserlock_addons.laser_lock.sws17101`

JDSU SWS17101 (TUNICS) tunable laser — native ASCII over GPIB (not SCPI).

```python
from laserlock_addons.laser_lock import sws17101
```

**Constants:** `MAX_POWER_DBM`, `OPTIONS`, `SETTLE_ENABLE_S`, `SETTLE_MOTOR_S`, `SETTLE_QUERY_S`

### class `SWS17101(resource: Optional[str] = None, inst=None, wl_min: float = 1500.0, wl_max: float = 1640.0)`

- `close(self) -> None`
- `safe_state(self) -> None`
- `query(self, cmd: str, settle: float = 0.3, ready_timeout: float = 2.0) -> Optional[str]`
- `query_float(self, cmd: str) -> Optional[float]`
- `write(self, cmd: str) -> None`
- `identify(self) -> Identity`
- `enable(self, confirm: bool = True) -> None` — Output on. (``confirm`` is accepted for older scripts and ignored.)
- `output_on(self, confirm: bool = True) -> None`
- `disable(self) -> None`
- `output_off(self) -> None`
- `set_power_uw(self, uw: float)`
- `is_on(self) -> Optional[bool]`
- `output_is_on(self) -> Optional[bool]`
- `set_wavelength_nm(self, wl_nm: float) -> Optional[float]`
- `set_wavelength(self, wl_nm: float) -> Optional[float]`
- `get_wavelength_nm(self) -> Optional[float]`
- `get_frequency_ghz(self) -> Optional[float]`
- `set_frequency_thz(self, thz: float)`
- `step(self, n_steps: int = 1)`
- `set_units_dbm(self)`
- `set_units_mw(self)`
- `set_unit(self, unit: str)`
- `set_power_dbm(self, dbm: float)`
- `set_power_w(self, watts: float)`
- `get_power_w(self) -> Optional[float]`
- `set_power(self, value: float, unit: str = dBm) -> Optional[float]`
- `get_power(self) -> Optional[float]`
- `set_speed(self, speed: int)`
- `get_speed(self)`
- `set_coherence_control(self, on: bool)` — Write-only on V4.02; the last value sent is remembered (unverified).
- `stepped_sweep(self, start_nm, stop_nm, step_nm, dwell_s=0.5, callback=None, stop_event=None, confirm: bool = True)`
- `poll(self) -> Dict[str, Any]`
- `snapshot(self) -> Dict[str, Any]`

