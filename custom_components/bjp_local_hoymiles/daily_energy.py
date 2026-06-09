"""Persistence helpers for daily energy values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, tzinfo
from typing import Any

from .parser import HoymilesSnapshot, InverterData, MpptData

MPPT_CACHE_SEPARATOR = ":"


@dataclass(frozen=True, slots=True)
class DailyEnergyCache:
    """Persisted daily energy cache for a single HA config entry."""

    day: date
    dtu_daily_energy_kwh: float | None = None
    inverter_daily_energy_kwh: dict[str, float] = field(default_factory=dict)
    mppt_daily_energy_kwh: dict[str, float] = field(default_factory=dict)


def restore_daily_energy_cache(
    snapshot: HoymilesSnapshot,
    cache: DailyEnergyCache | None,
    timezone: tzinfo,
) -> tuple[HoymilesSnapshot, DailyEnergyCache | None]:
    """Restore cached daily energy values for the same local day."""
    snapshot_day = _snapshot_day(snapshot, timezone)
    if snapshot_day is None:
        return snapshot, cache

    if cache is None or cache.day != snapshot_day:
        cache = DailyEnergyCache(day=snapshot_day)

    dtu_daily_energy_kwh, dtu_cache = _restore_value(
        snapshot.dtu_daily_energy_kwh,
        cache.dtu_daily_energy_kwh,
    )

    inverter_cache = dict(cache.inverter_daily_energy_kwh)
    inverters: list[InverterData] = []
    for inverter in snapshot.inverters:
        current_value, cached_value = _restore_value(
            inverter.daily_energy_kwh,
            inverter_cache.get(inverter.serial),
        )
        _update_cache_map(inverter_cache, inverter.serial, cached_value)
        inverters.append(
            replace(inverter, daily_energy_kwh=current_value),
        )

    mppt_cache = dict(cache.mppt_daily_energy_kwh)
    mppts: list[MpptData] = []
    for mppt in snapshot.mppts:
        mppt_key = _mppt_cache_key(mppt.inverter_serial, mppt.port_number)
        current_value, cached_value = _restore_value(
            mppt.daily_energy_kwh,
            mppt_cache.get(mppt_key),
        )
        _update_cache_map(mppt_cache, mppt_key, cached_value)
        mppts.append(
            replace(mppt, daily_energy_kwh=current_value),
        )

    return (
        replace(
            snapshot,
            dtu_daily_energy_kwh=dtu_daily_energy_kwh,
            inverters=tuple(inverters),
            mppts=tuple(mppts),
        ),
        DailyEnergyCache(
            day=snapshot_day,
            dtu_daily_energy_kwh=dtu_cache,
            inverter_daily_energy_kwh=inverter_cache,
            mppt_daily_energy_kwh=mppt_cache,
        ),
    )


def serialize_daily_energy_cache(cache: DailyEnergyCache) -> dict[str, Any]:
    """Convert a cache object into JSON-serializable storage data."""
    return {
        "day": cache.day.isoformat(),
        "dtu_daily_energy_kwh": cache.dtu_daily_energy_kwh,
        "inverter_daily_energy_kwh": cache.inverter_daily_energy_kwh,
        "mppt_daily_energy_kwh": cache.mppt_daily_energy_kwh,
    }


def deserialize_daily_energy_cache(
    data: Mapping[str, Any] | None,
) -> DailyEnergyCache | None:
    """Convert stored JSON data back into a cache object."""
    if not data:
        return None

    raw_day = data.get("day")
    if not isinstance(raw_day, str):
        return None

    try:
        parsed_day = date.fromisoformat(raw_day)
    except ValueError:
        return None

    inverter_cache = _deserialize_cache_map(data.get("inverter_daily_energy_kwh"))
    mppt_cache = _deserialize_cache_map(data.get("mppt_daily_energy_kwh"))
    if inverter_cache is None or mppt_cache is None:
        return None

    return DailyEnergyCache(
        day=parsed_day,
        dtu_daily_energy_kwh=_coerce_float(data.get("dtu_daily_energy_kwh")),
        inverter_daily_energy_kwh=inverter_cache,
        mppt_daily_energy_kwh=mppt_cache,
    )


def _snapshot_day(snapshot: HoymilesSnapshot, timezone: tzinfo) -> date | None:
    if snapshot.timestamp is None:
        return None
    return snapshot.timestamp.astimezone(timezone).date()


def _restore_value(
    current: float | None,
    cached: float | None,
) -> tuple[float | None, float | None]:
    if current is not None and current > 0:
        return current, current
    if cached is not None and cached > 0:
        return cached, cached
    return current, None


def _update_cache_map(
    cache_map: dict[str, float],
    key: str,
    value: float | None,
) -> None:
    if value is None:
        cache_map.pop(key, None)
        return
    cache_map[key] = value


def _mppt_cache_key(inverter_serial: str, port_number: int) -> str:
    return f"{inverter_serial}{MPPT_CACHE_SEPARATOR}{port_number}"


def _deserialize_cache_map(raw_value: Any) -> dict[str, float] | None:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        return None

    cache: dict[str, float] = {}
    for key, value in raw_value.items():
        if not isinstance(key, str):
            return None
        parsed_value = _coerce_float(value)
        if parsed_value is None or parsed_value <= 0:
            continue
        cache[key] = parsed_value
    return cache


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed
