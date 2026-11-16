# Written by Claude, guided by Chris.
"""The Tripp Lite PDU integration.

Creates one HA device per config entry (one entry per physical PDU), owned
by that entry as required by HA's device-registry model -- this is the
architecturally-correct replacement for the raw `sensor: platform: snmp` /
`switch: platform: snmp` YAML entities, not an external re-parenting of
those existing entities (HA only lets a config entry own its own devices,
so re-parenting YAML entities onto a device isn't an option).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_AUTH_KEY, DOMAIN, MANUFACTURER, MODEL
from .coordinator import PduCoordinator
from .snmp_client import PduSnmpClient

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = PduSnmpClient(
        entry.data[CONF_HOST], entry.data[CONF_USERNAME], entry.data[CONF_AUTH_KEY]
    )
    coordinator = PduCoordinator(hass, client, entry.data[CONF_HOST])
    await coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=MODEL,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
