# Written by Claude, guided by Chris.
"""Switch platform for the Tripp Lite PDU integration -- one entity per outlet.

Outlet count and names are discovered live from the device (not hardcoded),
since REC/Living/Master may not match MEC's 16 outlets exactly.

Displayed name is "Load N: <assigned name>" when the outlet has a real
assigned name (anything other than the device's own generic "Load N"
placeholder), or just "Load N" when it doesn't -- Chris wants the outlet
number visible everywhere he's given it a real name (UDM, USW, etc.),
without changing entity_id (which stays on the plain "Load N"-derived slug
it already has -- automations/scripts reference entity_id, not this
display name, so this is purely cosmetic and doesn't touch those).
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import PduCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PduCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PduOutletSwitch(coordinator, entry, outlet_num)
        for outlet_num in coordinator.data.outlets
    )


class PduOutletSwitch(CoordinatorEntity[PduCoordinator], SwitchEntity):
    _attr_has_entity_name = False  # outlet name from the device is already descriptive

    def __init__(
        self, coordinator: PduCoordinator, entry: ConfigEntry, outlet_num: int
    ) -> None:
        super().__init__(coordinator)
        self._outlet_num = outlet_num
        self._attr_unique_id = f"{entry.entry_id}_outlet_{outlet_num}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def name(self) -> str:
        generic = f"Load {self._outlet_num}"
        name, _ = self.coordinator.data.outlets.get(self._outlet_num, (generic, False))
        if name == generic:
            return generic
        return f"{generic}: {name}"

    @property
    def is_on(self) -> bool:
        _, is_on = self.coordinator.data.outlets.get(self._outlet_num, ("", False))
        return is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_outlet(self._outlet_num, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_outlet(self._outlet_num, False)
        await self.coordinator.async_request_refresh()
