# Written by Claude, guided by Chris.
"""Minimal async SNMPv3 client for Tripp Lite PDUMH15NET units.

Deliberately narrow -- just what this integration needs (whole-unit
metering read, outlet name/state table read, outlet state write). Not a
general-purpose SNMP library. Mirrors the exact pysnmp v3arch.asyncio
calling pattern already proven working this project in
Home Automation/snmp_probe.py.
"""

from __future__ import annotations

from pysnmp.hlapi.v3arch.asyncio import (
    ContextData,
    Integer,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    get_cmd,
    set_cmd,
    usmHMACMD5AuthProtocol,
    usmNoPrivProtocol,
    walk_cmd,
)

from homeassistant.exceptions import HomeAssistantError

from .const import (
    OID_OUTLET_COMMAND_BASE,
    OID_OUTLET_NAME_BASE,
    OID_OUTLET_STATE_BASE,
    OID_OUTPUT_CURRENT,
    OID_OUTPUT_POWER,
    OUTLET_STATE_OFF,
    OUTLET_STATE_ON,
)


class PduSnmpError(HomeAssistantError):
    """Raised when an SNMP operation against the PDU fails.

    Must subclass HomeAssistantError, not bare Exception -- HA's script
    engine's `continue_on_error: true` step option only suppresses
    HomeAssistantError subclasses (see homeassistant/helpers/script.py's
    _handle_exception: any other exception type is re-raised regardless of
    continue_on_error). Otherwise one failed outlet aborts a whole script
    even with continue_on_error on every step.
    """


class PduSnmpClient:
    """Talks SNMPv3 authNoPriv/MD5 to one Tripp Lite PDU.

    Reuses ONE SnmpEngine and ONE UdpTransportTarget for the client's whole
    lifetime instead of creating a fresh one per call. Originally each call
    created its own engine (a fresh SNMPv3 engine-discovery/time-sync
    handshake every time, plus never-closed sockets/dispatchers -- a real
    resource leak). Live testing against a real PDU also showed a coordinator
    cycle calling get_cmd immediately followed by two back-to-back walk_cmd
    calls, each with a brand-new engine, sometimes got confused/partial
    results from the device's embedded SNMP agent (outlets 1-8 silently
    missing from a walk that returns all 16 when run in isolation). A
    single shared engine avoids both problems.
    """

    def __init__(self, host: str, username: str, auth_key: str) -> None:
        self._host = host
        self._user = UsmUserData(
            username,
            authKey=auth_key,
            authProtocol=usmHMACMD5AuthProtocol,
            privProtocol=usmNoPrivProtocol,
        )
        self._engine = SnmpEngine()
        self._target = None

    async def _get_target(self):
        if self._target is not None:
            return self._target
        try:
            self._target = await UdpTransportTarget.create(
                (self._host, 161), timeout=5, retries=1
            )
        except Exception as err:
            # UdpTransportTarget.create() resolves the hostname and can
            # raise a raw socket/OS exception (e.g. DNS failure) that isn't
            # a PduSnmpError -- config_flow.py only catches PduSnmpError,
            # so an unwrapped exception here surfaces as HA's generic
            # "Unknown error occurred" instead of our own cannot_connect
            # message. Wrap it so every real-world connection failure --
            # bad hostname, unreachable host, SNMP error alike -- reports
            # the same way.
            raise PduSnmpError(
                f"{self._host}: failed to resolve/connect: {err}"
            ) from err
        return self._target

    async def async_get_metering(self) -> tuple[float, int]:
        """Return (current_amps, power_watts) for the whole PDU."""
        target = await self._get_target()
        err_ind, err_stat, _, var_binds = await get_cmd(
            self._engine,
            self._user,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(OID_OUTPUT_CURRENT)),
            ObjectType(ObjectIdentity(OID_OUTPUT_POWER)),
        )
        if err_ind or err_stat:
            raise PduSnmpError(f"{self._host}: {err_ind or err_stat}")
        raw_current, raw_power = (int(vb[1]) for vb in var_binds)
        return raw_current / 100, raw_power

    async def async_get_outlets(self) -> dict[int, tuple[str, bool]]:
        """Return {outlet_number: (name, is_on)} for every outlet the PDU reports."""
        names = await self._walk_suffixed(OID_OUTLET_NAME_BASE)
        states = await self._walk_suffixed(OID_OUTLET_STATE_BASE)
        outlets: dict[int, tuple[str, bool]] = {}
        for outlet_num, name in names.items():
            state = states.get(outlet_num)
            is_on = int(state) == OUTLET_STATE_ON if state is not None else False
            outlets[outlet_num] = (str(name), is_on)
        return outlets

    async def async_set_outlet(self, outlet_num: int, turn_on: bool) -> None:
        target = await self._get_target()
        value = OUTLET_STATE_ON if turn_on else OUTLET_STATE_OFF
        # See const.py's OID_OUTLET_COMMAND_BASE docstring: writes must
        # target the separate "command" column (6), not
        # the read-only "status" column (4) that OID_OUTLET_STATE_BASE points at
        # and that this method originally (wrongly) wrote to.
        oid = f"{OID_OUTLET_COMMAND_BASE}.{outlet_num}"
        err_ind, err_stat, _, _ = await set_cmd(
            self._engine,
            self._user,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(oid), Integer(str(value))),
        )
        if err_ind or err_stat:
            raise PduSnmpError(
                f"{self._host}: failed to set outlet {outlet_num}: {err_ind or err_stat}"
            )

    async def _walk_suffixed(self, base_oid: str) -> dict[int, object]:
        """Walk a table column, keyed by the last OID index (the outlet number).

        lexicographicMode=False is required here -- pysnmp's walk_cmd
        defaults to True ("walk the agent's MIB till the end"), which does
        NOT stop at the end of base_oid's subtree. Without this, a live
        test against a real PDU walked straight past the last real outlet
        entry into unrelated parts of the device's MIB tree (landing on
        what looked like a raw SNMP engine ID), and this method's naive
        per-row collection loop happily stored those bogus rows as if they
        were more outlets -- surfaced as `int()` crashing on raw bytes
        downstream in async_get_outlets(). lexicographicMode=False makes
        the walk stop cleanly once results leave base_oid's subtree.
        """
        target = await self._get_target()
        results: dict[int, object] = {}
        async for err_ind, err_stat, _, var_binds in walk_cmd(
            self._engine,
            self._user,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(base_oid)),
            lexicographicMode=False,
        ):
            if err_ind or err_stat:
                raise PduSnmpError(f"{self._host}: {err_ind or err_stat}")
            for oid, value in var_binds:
                outlet_num = int(str(oid).rsplit(".", 1)[-1])
                results[outlet_num] = value
        return results
