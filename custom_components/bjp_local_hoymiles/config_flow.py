"""Config flow for BJP Local Hoymiles."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er

from .billing_wizard import (
    BillingHelperRecipe,
    BillingWizardError,
    build_billing_cron,
    build_review_text,
    find_existing_utility_meter_helpers,
)
from .client import (
    CannotConnectError,
    InvalidResponseError,
    ReadOnlyHoymilesClient,
)
from .const import (
    BILLING_CYCLE_MODE_ADVANCED_CRON,
    BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
    BILLING_RESET_DAY_LAST,
    CONF_BILLING_CRON,
    CONF_BILLING_CYCLE_ENABLED,
    CONF_BILLING_CYCLE_MODE,
    CONF_BILLING_RESET_DAY,
    CONF_BILLING_RESET_TIME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_BILLING_RESET_TIME,
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


class BjpLocalHoymilesConfigFlow(  # type: ignore[call-arg]
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
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
        self._pending_options: dict[str, Any] = {}
        self._review_text = ""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self._pending_options = self._merged_options(user_input)
            if not user_input[CONF_BILLING_CYCLE_ENABLED]:
                return self.async_create_entry(title="", data=self._pending_options)
            return await self.async_step_billing()

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
                    ),
                    vol.Required(
                        CONF_BILLING_CYCLE_ENABLED,
                        default=self._config_entry.options.get(
                            CONF_BILLING_CYCLE_ENABLED,
                            False,
                        ),
                    ): bool,
                }
            ),
        )

    async def async_step_billing(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect billing cycle settings for Utility Meter helper guidance."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                cron = build_billing_cron(
                    user_input[CONF_BILLING_CYCLE_MODE],
                    user_input.get(CONF_BILLING_RESET_DAY, ""),
                    user_input.get(CONF_BILLING_RESET_TIME, ""),
                    user_input.get(CONF_BILLING_CRON, ""),
                )
            except BillingWizardError as err:
                errors["base"] = str(err)
            else:
                self._pending_options = self._merged_options(
                    {**user_input, CONF_BILLING_CRON: cron}
                )
                self._review_text = self._build_review_text(cron)
                return await self.async_step_review()

        defaults = (
            self._merged_options(user_input)
            if user_input is not None
            else (self._pending_options or self._config_entry.options)
        )
        mode = defaults.get(
            CONF_BILLING_CYCLE_MODE,
            BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
        )
        schema_fields: dict[Any, Any] = {
            vol.Required(
                CONF_BILLING_CYCLE_MODE,
                default=mode,
            ): vol.In(
                [
                    BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
                    BILLING_CYCLE_MODE_ADVANCED_CRON,
                ]
            ),
        }

        if mode == BILLING_CYCLE_MODE_SIMPLE_MONTHLY:
            schema_fields[
                vol.Required(
                    CONF_BILLING_RESET_DAY,
                    default=defaults.get(CONF_BILLING_RESET_DAY, "1"),
                )
            ] = vol.In([*(str(day) for day in range(1, 29)), BILLING_RESET_DAY_LAST])
            schema_fields[
                vol.Required(
                    CONF_BILLING_RESET_TIME,
                    default=defaults.get(
                        CONF_BILLING_RESET_TIME,
                        DEFAULT_BILLING_RESET_TIME,
                    ),
                )
            ] = str
        else:
            schema_fields[
                vol.Required(
                    CONF_BILLING_CRON,
                    default=defaults.get(CONF_BILLING_CRON, "0 0 1 * *"),
                )
            ] = str

        return self.async_show_form(
            step_id="billing",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    async def async_step_review(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show the Utility Meter helper recipe generated from billing options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=self._pending_options)

        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema({}),
            description_placeholders={"review_text": self._review_text},
        )

    def _merged_options(self, updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(self._config_entry.options)
        merged.update(updates)
        return merged

    def _build_review_text(self, cron: str) -> str:
        import_source, export_source = self._resolve_billing_source_entities()
        utility_entries = self.hass.config_entries.async_entries("utility_meter")
        import_recipe = BillingHelperRecipe(
            label="From Grid helper",
            source_entity_id=import_source,
            cron=cron,
            existing_helpers=find_existing_utility_meter_helpers(
                utility_entries,
                import_source,
            ),
        )
        export_recipe = BillingHelperRecipe(
            label="To Grid helper",
            source_entity_id=export_source,
            cron=cron,
            existing_helpers=find_existing_utility_meter_helpers(
                utility_entries,
                export_source,
            ),
        )
        return build_review_text(import_recipe, export_recipe)

    def _resolve_billing_source_entities(self) -> tuple[str, str]:
        entity_registry = er.async_get(self.hass)
        import_source: str | None = None
        export_source: str | None = None

        for entity_entry in entity_registry.entities.values():
            if entity_entry.config_entry_id != self._config_entry.entry_id:
                continue
            if entity_entry.domain != "sensor":
                continue
            if entity_entry.unique_id.endswith("_lifetime_imported_energy"):
                import_source = entity_entry.entity_id
            if entity_entry.unique_id.endswith("_lifetime_exported_energy"):
                export_source = entity_entry.entity_id

        if import_source and export_source:
            return import_source, export_source

        coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if (
            coordinator is not None
            and getattr(coordinator, "data", None)
            and coordinator.data.meters
        ):
            meter_serial = coordinator.data.meters[0].serial
            return (
                import_source
                or f"sensor.hoymiles_meter_{meter_serial}_lifetime_imported_energy",
                export_source
                or f"sensor.hoymiles_meter_{meter_serial}_lifetime_exported_energy",
            )

        return (
            import_source or "sensor.hoymiles_meter_<serial>_lifetime_imported_energy",
            export_source or "sensor.hoymiles_meter_<serial>_lifetime_exported_energy",
        )
