"""Diagnostics support for BJP Local Hoymiles."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, DOMAIN
from .coordinator import BjpLocalHoymilesCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: BjpLocalHoymilesCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data

    diagnostics: dict[str, Any] = {
        "entry": {
            **entry.data,
            CONF_HOST: _redact_host(entry.data.get(CONF_HOST)),
        },
        "last_update_success": coordinator.last_update_success,
        "snapshot": None,
    }

    if data is not None:
        diagnostics["snapshot"] = {
            "dtu_serial": _redact_serial(data.dtu_serial),
            "timestamp": data.timestamp.isoformat() if data.timestamp else None,
            "meters": len(data.meters),
            "inverters": len(data.inverters),
            "mppts": len(data.mppts),
            "dtu_power_w": data.dtu_power_w,
            "home_load_power_w": data.home_load_power_w,
        }

    return diagnostics


def _redact_host(host: str | None) -> str | None:
    if host is None:
        return None
    parts = host.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return ".".join([parts[0], parts[1], "x", "x"])
    return "<redacted>"


def _redact_serial(serial: str | None) -> str | None:
    if not serial:
        return serial
    if len(serial) <= 4:
        return "****"
    return f"{serial[:4]}****{serial[-2:]}"
