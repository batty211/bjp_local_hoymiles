"""Data update coordinator for BJP Local Hoymiles."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CannotConnectError, InvalidResponseError, ReadOnlyHoymilesClient
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .parser import HoymilesSnapshot

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

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> HoymilesSnapshot:
        """Fetch data from the DTU."""
        try:
            return await self.client.async_get_snapshot()
        except (CannotConnectError, InvalidResponseError) as err:
            raise UpdateFailed(str(err)) from err
