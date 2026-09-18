# Written by Claude, guided by Chris.
"""Config flow for the Tripp Lite PDU integration.

Deliberately validates against the live device before creating the entry
(one bad-credentials incident this project already had this session was
enough) -- if the SNMP read fails, the form re-shows with an error instead
of silently creating a broken config entry.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_AUTH_KEY, DEFAULT_USERNAME, DOMAIN
from .snmp_client import PduSnmpClient, PduSnmpError

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_AUTH_KEY): str,
    }
)


class TrippLitePduConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One config entry per physical PDU."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            client = PduSnmpClient(
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_AUTH_KEY],
            )
            try:
                current, power = await client.async_get_metering()
            except PduSnmpError:
                _LOGGER.exception(
                    "Failed to validate PDU at %s", user_input[CONF_HOST]
                )
                errors["base"] = "cannot_connect"
            else:
                _LOGGER.debug(
                    "Validated PDU %s: current=%.2fA power=%dW",
                    user_input[CONF_HOST],
                    current,
                    power,
                )
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
