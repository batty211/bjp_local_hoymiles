"""Data update coordinator for BJP Local Hoymiles."""

from __future__ import annotations

import logging
from datetime import UTC, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
from .parser import HoymilesSnapshot, preserve_daily_energy_for_same_day

_LOGGER = logging.getLogger(__name__)


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

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> HoymilesSnapshot:
        """Fetch data from the DTU."""
        try:
            snapshot = await self.client.async_get_snapshot()
        except (CannotConnectError, InvalidResponseError) as err:
            raise UpdateFailed(str(err)) from err
        return preserve_daily_energy_for_same_day(
            snapshot,
            self.data,
            self._timezone,
        )


def _timezone_from_hass(hass: HomeAssistant) -> tzinfo:
    if not hass.config.time_zone:
        return UTC
    try:
        return ZoneInfo(hass.config.time_zone)
    except (TypeError, ZoneInfoNotFoundError):
        return UTC
