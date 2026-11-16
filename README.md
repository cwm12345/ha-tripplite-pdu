# Tripp Lite PDU for Home Assistant

A `config_entry`-owned Home Assistant custom integration for Tripp Lite
**PDUMH15NET** (metered + switched, network-managed) PDUs over SNMPv3.
Each PDU shows up as a proper HA **device**, with its outlets as switch
entities and its whole-unit metering as sensor entities — instead of the
flat, deviceless entity pile you get from hand-written
`sensor: platform: snmp` / `switch: platform: snmp` YAML.

## Status

This is a working reference implementation, pulled from my own running
Home Assistant deployment (four PDUMH15NET units) and published as-is. **I
am not maintaining this as an ongoing package** — no commitment to triage
issues, accept PRs, or track future Home Assistant API changes. Feel free
to fork it, adapt it, or copy pieces of it into your own setup. If it's
useful, great; if you hit something that doesn't work on your hardware or
your HA version, you're welcome to open an issue, but I can't promise a
response.

If you're a more serious maintainer and see something here worth turning
into an official core Home Assistant integration, take it — this code is
public domain (Unlicense), no permission needed and none of this project's
"not maintained" framing should discourage you from picking it up.

## Why this exists

Tripp Lite doesn't publish a supported Home Assistant integration for
these PDUs, and no maintained HACS-listed one exists for this model. Core
HA's `snmp` platform works for reading values but has no way to group its
entities under a device — and per HA's own architecture, a device can
only be created by the config entry that owns it, not attached from
outside. This integration exists to close that specific gap.

## Hardware this was built and tested against

Tripp Lite **PDUMH15NET** (15A/120V, metered + switched, network
management card / WEBCARDLX), SNMPv3 authNoPriv/MD5. Other PDUMH-family
models using the same MIB (`TRIPPLITE-PRODUCTS.MIB`) may work but haven't
been tested.

**Known hardware limitation, not a bug in this integration:** these units
only expose whole-PDU/whole-circuit current and power (confirmed via
direct MIB walk) — per-outlet metering OIDs exist in the MIB but return
`ERROR_NO_SUCH_NAME` on this hardware. If you need per-outlet power draw,
this model can't give it to you over SNMP; this integration doesn't
pretend otherwise.

## What it does

- One config entry per physical PDU (Settings → Devices & Services → Add
  Integration → "Tripp Lite PDU", once per unit).
- Creates one HA device per entry, with:
  - 2 sensors: Total Current (A), Total Power (W).
  - N outlet switches, discovered live from the device (not hardcoded —
    outlet count varies by model/config), named from whatever you've
    already labeled them on the PDU itself.
- Polls every 30s via a `DataUpdateCoordinator`.
- Validates the SNMP connection before creating the config entry — bad
  host/credentials show an error in the form instead of silently creating
  a broken entry.

## What it deliberately does not do

- Per-outlet metering (see hardware limitation above).
- Modify or remove any existing `snmp:` YAML entities — this runs
  alongside them, doesn't replace them automatically.

## Installation

**With HACS:**

1. In Home Assistant, open **HACS**, then the **⋮** menu (top right) →
   **Custom repositories**.
2. Repository: `https://github.com/cwm12345/ha-tripplite-pdu`, type:
   **Integration**. Click **Add**.
3. Search HACS for **Tripp Lite PDU**, open it and click **Download**.
4. Restart Home Assistant.

**Manual:** copy `custom_components/tripplite_pdu/` into your HA config's
`custom_components/` directory → restart HA.

Then: Settings → Devices & Services → Add Integration → "Tripp Lite PDU".
Enter the PDU's hostname/IP and its SNMPv3 username + auth key (whatever
you've configured on the PDU's own management interface).

## Files

- `const.py` — the SNMP OIDs (confirmed by live MIB walk, not guessed
  from the MIB file alone) and other constants.
- `snmp_client.py` — a minimal async SNMPv3 client scoped to exactly what
  this integration needs (metering read, outlet table read/write).
  Reuses one `SnmpEngine` for the client's lifetime rather than
  recreating it per call.
- `coordinator.py` — the `DataUpdateCoordinator` polling loop.
- `config_flow.py` — setup UI, validates against the live device.
- `__init__.py` — creates the device via
  `device_registry.async_get_or_create()`.
- `sensor.py` / `switch.py` — the entity platforms.
- `strings.json` / `translations/en.json` — config flow + entity text.

## Validation

All files pass `py_compile` / JSON validation, every module imports
cleanly against a real installed `homeassistant` package, and the config
flow self-registers correctly. Deployed and running against real hardware
(four physical PDUs) since September 2026.
