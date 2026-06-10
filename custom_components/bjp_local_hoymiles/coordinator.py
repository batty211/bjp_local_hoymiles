"""Data update coordinator for BJP Local Hoymiles."""

from __future__ import annotations

import logging
from datetime import UTC, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .client import CannotConnectError, InvalidResponseError, ReadOnlyHoymilesClient
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .daily_energy import (
    DailyEnergyCache,
    deserialize_daily_energy_cache,
    restore_daily_energy_cache,
    serialize_daily_energy_cache,
)
from .meter_lifetime import (
    MeterLifetimeCache,
    deserialize_meter_lifetime_cache,
    meter_lifetime_cache_needs_migration,
    restore_meter_lifetime_cache,
    serialize_meter_lifetime_cache,
)
from .parser import HoymilesSnapshot, preserve_meter_lifetime_energy

_LOGGER = logging.getLogger(__name__)
_DAILY_ENERGY_STORE_VERSION = 1
_METER_LIFETIME_STORE_VERSION = 1


class BjpLocalHoymilesCoordinator(DataUpdateCoordinator[HoymilesSnapshot]):
    """Coordinator that polls a Hoymiles DTU."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.config_entry = entry
        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        self.client = ReadOnlyHoymilesClient(host=host, port=port)
        self._timezone = _timezone_from_hass(hass)
        self._daily_energy_store = Store(
            hass,
            _DAILY_ENERGY_STORE_VERSION,
            f"{DOMAIN}.daily_energy_cache_{entry.entry_id}",
        )
        self._daily_energy_cache: DailyEnergyCache | None = None
        self._meter_lifetime_store = Store(
            hass,
            _METER_LIFETIME_STORE_VERSION,
            f"{DOMAIN}.meter_lifetime_cache_{entry.entry_id}",
        )
        self._meter_lifetime_cache: MeterLifetimeCache | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def async_initialize(self) -> None:
        """Load persisted energy caches before polling starts."""
        self._daily_energy_cache = deserialize_daily_energy_cache(
            await self._daily_energy_store.async_load(),
        )
        stored_meter_cache = await self._meter_lifetime_store.async_load()
        self._meter_lifetime_cache = deserialize_meter_lifetime_cache(
            stored_meter_cache,
        )
        if (
            self._meter_lifetime_cache is not None
            and meter_lifetime_cache_needs_migration(stored_meter_cache)
        ):
            try:
                await self._meter_lifetime_store.async_save(
                    serialize_meter_lifetime_cache(self._meter_lifetime_cache),
                )
            except Exception:  # pragma: no cover - best effort persistence
                _LOGGER.exception("Failed to migrate meter lifetime cache")

    async def _async_update_data(self) -> HoymilesSnapshot:
        """Fetch data from the DTU."""
        try:
            snapshot = await self.client.async_get_snapshot()
        except (CannotConnectError, InvalidResponseError) as err:
            raise UpdateFailed(str(err)) from err

        restored_snapshot, updated_cache = restore_daily_energy_cache(
            snapshot,
            self._daily_energy_cache,
            self._timezone,
        )
        restored_snapshot = preserve_meter_lifetime_energy(
            restored_snapshot,
            self.data,
        )
        restored_snapshot, updated_meter_cache = restore_meter_lifetime_cache(
            restored_snapshot,
            self._meter_lifetime_cache,
        )
        if updated_cache != self._daily_energy_cache:
            self._daily_energy_cache = updated_cache
            if updated_cache is not None:
                try:
                    await self._daily_energy_store.async_save(
                        serialize_daily_energy_cache(updated_cache),
                    )
                except Exception:  # pragma: no cover - best effort persistence
                    _LOGGER.exception("Failed to save daily energy cache")
        if updated_meter_cache != self._meter_lifetime_cache:
            self._meter_lifetime_cache = updated_meter_cache
            if updated_meter_cache is not None:
                try:
                    await self._meter_lifetime_store.async_save(
                        serialize_meter_lifetime_cache(updated_meter_cache),
                    )
                except Exception:  # pragma: no cover - best effort persistence
                    _LOGGER.exception("Failed to save meter lifetime cache")
        return restored_snapshot


def _timezone_from_hass(hass: HomeAssistant) -> tzinfo:
    if not hass.config.time_zone:
        return UTC
    try:
        return ZoneInfo(hass.config.time_zone)
    except (TypeError, ZoneInfoNotFoundError):
        return UTC
