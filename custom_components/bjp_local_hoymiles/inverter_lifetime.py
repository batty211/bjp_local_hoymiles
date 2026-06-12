"""Persistence helpers for inverter and MPPT lifetime energy values."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .parser import (
    HoymilesSnapshot,
    MpptData,
    preserve_inverter_lifetime_energy,
    rebuild_meter_derived_energy,
)


@dataclass(frozen=True, slots=True)
class InverterLifetimeCache:
    """Persisted MPPT lifetime cache for a single HA config entry."""

    mppt_lifetime_energy_kwh: dict[str, float] = field(default_factory=dict)


def restore_inverter_lifetime_cache(
    snapshot: HoymilesSnapshot,
    cache: InverterLifetimeCache | None,
) -> tuple[HoymilesSnapshot, InverterLifetimeCache | None]:
    """Restore cached MPPT lifetime values across coordinator restarts."""
    if not snapshot.mppts:
        return snapshot, cache

    if cache is None:
        cache = InverterLifetimeCache()

    mppt_cache = dict(cache.mppt_lifetime_energy_kwh)

    mppts: list[MpptData] = []
    for mppt in snapshot.mppts:
        cache_key = _mppt_cache_key(mppt.inverter_serial, mppt.port_number)
        restored_value, cached_value = _restore_value(
            mppt.lifetime_energy_kwh,
            mppt_cache.get(cache_key),
        )
        _update_cache_map(mppt_cache, cache_key, cached_value)
        mppts.append(replace(mppt, lifetime_energy_kwh=restored_value))

    restored_snapshot = preserve_inverter_lifetime_energy(
        replace(snapshot, mppts=tuple(mppts)),
        snapshot,
    )
    restored_snapshot = rebuild_meter_derived_energy(
        restored_snapshot,
        restored_snapshot.meters,
    )
    updated_cache = InverterLifetimeCache(mppt_lifetime_energy_kwh=mppt_cache)
    if not mppt_cache:
        return restored_snapshot, None
    return restored_snapshot, updated_cache


def serialize_inverter_lifetime_cache(cache: InverterLifetimeCache) -> dict[str, Any]:
    """Convert a cache object into JSON-serializable storage data."""
    return {
        "mppt_lifetime_energy_kwh": cache.mppt_lifetime_energy_kwh,
    }


def deserialize_inverter_lifetime_cache(
    data: dict[str, Any] | None,
) -> InverterLifetimeCache | None:
    """Convert stored JSON data back into a cache object."""
    if not data:
        return None

    mppt_cache = _deserialize_cache_map(data.get("mppt_lifetime_energy_kwh"))
    if mppt_cache is None or not mppt_cache:
        return None

    return InverterLifetimeCache(mppt_lifetime_energy_kwh=mppt_cache)


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


def _mppt_cache_key(inverter_serial: str, port_number: int) -> str:
    return f"{inverter_serial}:{port_number}"
