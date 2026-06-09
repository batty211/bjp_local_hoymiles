"""Persistence helpers for meter lifetime energy values."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .parser import HoymilesSnapshot, MeterData, rebuild_meter_derived_energy


@dataclass(frozen=True, slots=True)
class MeterLifetimeCache:
    """Persisted meter lifetime cache for a single HA config entry."""

    meter_lifetime_imported_energy_kwh: dict[str, float] = field(
        default_factory=dict
    )
    meter_lifetime_exported_energy_kwh: dict[str, float] = field(
        default_factory=dict
    )


def restore_meter_lifetime_cache(
    snapshot: HoymilesSnapshot,
    cache: MeterLifetimeCache | None,
) -> tuple[HoymilesSnapshot, MeterLifetimeCache | None]:
    """Restore cached meter lifetime values across coordinator restarts."""
    if not snapshot.meters:
        return snapshot, cache

    if cache is None:
        cache = MeterLifetimeCache()

    imported_cache = dict(cache.meter_lifetime_imported_energy_kwh)
    exported_cache = dict(cache.meter_lifetime_exported_energy_kwh)

    meters: list[MeterData] = []
    for meter in snapshot.meters:
        imported_value, imported_cached = _restore_value(
            meter.lifetime_imported_energy_kwh,
            imported_cache.get(meter.serial),
        )
        _update_cache_map(imported_cache, meter.serial, imported_cached)

        exported_value, exported_cached = _restore_value(
            meter.lifetime_exported_energy_kwh,
            exported_cache.get(meter.serial),
        )
        _update_cache_map(exported_cache, meter.serial, exported_cached)

        meters.append(
            replace(
                meter,
                lifetime_imported_energy_kwh=imported_value,
                lifetime_exported_energy_kwh=exported_value,
            )
        )

    updated_cache = MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh=imported_cache,
        meter_lifetime_exported_energy_kwh=exported_cache,
    )
    if not imported_cache and not exported_cache:
        return rebuild_meter_derived_energy(snapshot, tuple(meters)), None

    return (
        rebuild_meter_derived_energy(snapshot, tuple(meters)),
        updated_cache,
    )


def serialize_meter_lifetime_cache(cache: MeterLifetimeCache) -> dict[str, Any]:
    """Convert a cache object into JSON-serializable storage data."""
    return {
        "meter_lifetime_imported_energy_kwh": cache.meter_lifetime_imported_energy_kwh,
        "meter_lifetime_exported_energy_kwh": cache.meter_lifetime_exported_energy_kwh,
    }


def deserialize_meter_lifetime_cache(
    data: dict[str, Any] | None,
) -> MeterLifetimeCache | None:
    """Convert stored JSON data back into a cache object."""
    if not data:
        return None

    imported_cache = _deserialize_cache_map(
        data.get("meter_lifetime_imported_energy_kwh")
    )
    exported_cache = _deserialize_cache_map(
        data.get("meter_lifetime_exported_energy_kwh")
    )
    if imported_cache is None or exported_cache is None:
        return None

    if not imported_cache and not exported_cache:
        return None

    return MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh=imported_cache,
        meter_lifetime_exported_energy_kwh=exported_cache,
    )


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
