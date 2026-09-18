# Written by Claude, guided by Chris.
"""Sensor platform for the Tripp Lite PDU integration -- whole-unit metering."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
        [PduCurrentSensor(coordinator, entry), PduPowerSensor(coordinator, entry)]
    )


class _PduSensorBase(CoordinatorEntity[PduCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PduCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )


class PduCurrentSensor(_PduSensorBase):
    _attr_translation_key = "total_current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = "A"

    def __init__(self, coordinator: PduCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current"

    @property
    def native_value(self) -> float:
        return self.coordinator.data.current_amps


class PduPowerSensor(_PduSensorBase):
    _attr_translation_key = "total_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"

    def __init__(self, coordinator: PduCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_power"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.power_watts
