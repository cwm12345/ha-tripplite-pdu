# Written by Claude, guided by Chris.
"""DataUpdateCoordinator for the Tripp Lite PDU integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL
from .snmp_client import PduSnmpClient, PduSnmpError

_LOGGER = logging.getLogger(__name__)


@dataclass
class PduData:
    current_amps: float
    power_watts: int
    outlets: dict[int, tuple[str, bool]]  # {outlet_num: (name, is_on)}


class PduCoordinator(DataUpdateCoordinator[PduData]):
    """Polls one PDU on a fixed interval; also used directly for outlet writes."""

    def __init__(self, hass: HomeAssistant, client: PduSnmpClient, host: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"tripplite_pdu_{host}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> PduData:
        try:
            current, power = await self.client.async_get_metering()
            outlets = await self.client.async_get_outlets()
        except PduSnmpError as err:
            raise UpdateFailed(str(err)) from err
        return PduData(current_amps=current, power_watts=power, outlets=outlets)
