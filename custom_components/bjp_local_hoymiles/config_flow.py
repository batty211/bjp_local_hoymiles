"""Config flow for BJP Local Hoymiles."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .client import CannotConnectError, InvalidResponseError, ReadOnlyHoymilesClient
from .const import (
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT,
                default=defaults.get(CONF_PORT, DEFAULT_PORT),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


class BjpLocalHoymilesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a BJP Local Hoymiles config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            result = await self._async_validate_input(user_input)
            if result is None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=_schema(user_input),
                    errors={"base": "cannot_connect"},
                )
            if isinstance(result, str):
                return self.async_show_form(
                    step_id="user",
                    data_schema=_schema(user_input),
                    errors={"base": result},
                )

            await self.async_set_unique_id(result.dtu_serial)
            self._abort_if_unique_id_configured(
                updates={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                }
            )
            return self.async_create_entry(
                title=f"BJP Local Hoymiles {result.dtu_serial}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle reconfiguration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        defaults = dict(entry.data)

        if user_input is not None:
            result = await self._async_validate_input(user_input)
            if result is None:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=_schema(user_input),
                    errors={"base": "cannot_connect"},
                )
            if isinstance(result, str):
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=_schema(user_input),
                    errors={"base": result},
                )

            await self.async_set_unique_id(result.dtu_serial)
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                entry,
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(defaults),
        )

    async def _async_validate_input(self, user_input: dict[str, Any]) -> Any:
        """Validate the user input by fetching a snapshot."""
        client = ReadOnlyHoymilesClient(
            host=user_input[CONF_HOST],
            port=user_input[CONF_PORT],
        )
        try:
            return await client.async_get_snapshot()
        except CannotConnectError:
            return None
        except InvalidResponseError:
            return "invalid_response"

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BjpLocalHoymilesOptionsFlow:
        """Create the options flow."""
        return BjpLocalHoymilesOptionsFlow(config_entry)


class BjpLocalHoymilesOptionsFlow(config_entries.OptionsFlow):
    """Handle options for BJP Local Hoymiles."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self._config_entry.data.get(
                                CONF_SCAN_INTERVAL,
                                DEFAULT_SCAN_INTERVAL,
                            ),
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
