"""Payload parser for Hoymiles DTU real-time data."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, tzinfo
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _number(value: Any, scale: float = 1.0) -> float | None:
    if value is None or value == "":
        return None
    return round(float(value) / scale, 6)


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _serial(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=UTC)


@dataclass(frozen=True, slots=True)
class MeterData:
    """Normalized meter values."""

    serial: str
    device_type: int | None
    net_grid_power_w: float | None
    grid_import_power_w: float | None
    grid_export_power_w: float | None
    voltage_v: float | None
    current_a: float | None
    power_factor: float | None
    lifetime_exported_energy_kwh: float | None
    lifetime_imported_energy_kwh: float | None
    fault_code: int | None


@dataclass(frozen=True, slots=True)
class InverterData:
    """Normalized inverter values."""

    serial: str
    firmware_version: int | None
    voltage_v: float | None
    frequency_hz: float | None
    active_power_w: float | None
    current_a: float | None
    power_factor: float | None
    temperature_c: float | None
    warning_number: int | None
    link_status: int | None
    signal_dbm: int | None
    daily_energy_kwh: float | None
    lifetime_energy_kwh: float | None


@dataclass(frozen=True, slots=True)
class MpptData:
    """Normalized MPPT/PV port values."""

    inverter_serial: str
    port_number: int
    voltage_v: float | None
    current_a: float | None
    power_w: float | None
    daily_energy_kwh: float | None
    lifetime_energy_kwh: float | None
    error_code: int | None


@dataclass(frozen=True, slots=True)
class HoymilesSnapshot:
    """Normalized real-time DTU snapshot."""

    dtu_serial: str
    timestamp: datetime | None
    ap: int | None
    cp: int | None
    firmware_version: int | None
    dtu_power_w: float | None
    dtu_daily_energy_kwh: float | None
    lifetime_solar_energy_kwh: float | None
    solar_self_consumed_energy_kwh: float | None
    home_consumption_energy_kwh: float | None
    home_load_power_w: float | None
    meters: tuple[MeterData, ...]
    inverters: tuple[InverterData, ...]
    mppts: tuple[MpptData, ...]


def parse_snapshot(payload: Mapping[str, Any]) -> HoymilesSnapshot:
    """Normalize a real-data-new payload from hoymiles-wifi."""
    meters = tuple(_parse_meter(item) for item in payload.get("meterData", []))
    mppts = tuple(_parse_mppt(item) for item in payload.get("pvData", []))

    mppt_daily_by_inverter: dict[str, float] = {}
    mppt_lifetime_by_inverter: dict[str, float] = {}
    for mppt in mppts:
        if mppt.daily_energy_kwh is not None:
            mppt_daily_by_inverter[mppt.inverter_serial] = (
                mppt_daily_by_inverter.get(mppt.inverter_serial, 0.0)
                + mppt.daily_energy_kwh
            )
        if mppt.lifetime_energy_kwh is not None:
            mppt_lifetime_by_inverter[mppt.inverter_serial] = (
                mppt_lifetime_by_inverter.get(mppt.inverter_serial, 0.0)
                + mppt.lifetime_energy_kwh
            )

    inverters = tuple(
        _parse_inverter(item, mppt_daily_by_inverter, mppt_lifetime_by_inverter)
        for item in payload.get("sgsData", [])
    )

    total_mppt_daily_energy_kwh = (
        round(sum(mppt_daily_by_inverter.values()), 6)
        if mppt_daily_by_inverter
        else None
    )
    dtu_power_w = _number(payload.get("dtuPower"), 10)
    reported_dtu_daily_energy_kwh = _number(payload.get("dtuDailyEnergy"), 1000)
    dtu_daily_energy_kwh = (
        total_mppt_daily_energy_kwh
        if reported_dtu_daily_energy_kwh in (None, 0.0)
        and total_mppt_daily_energy_kwh is not None
        else reported_dtu_daily_energy_kwh
    )
    lifetime_solar_energy_kwh = (
        round(sum(mppt_lifetime_by_inverter.values()), 6)
        if mppt_lifetime_by_inverter
        else None
    )

    primary_meter = meters[0] if meters else None
    lifetime_imported_energy_kwh = (
        primary_meter.lifetime_imported_energy_kwh
        if primary_meter is not None
        else None
    )
    lifetime_exported_energy_kwh = (
        primary_meter.lifetime_exported_energy_kwh
        if primary_meter is not None
        else None
    )
    solar_self_consumed_energy_kwh = None
    if (
        lifetime_solar_energy_kwh is not None
        and lifetime_exported_energy_kwh is not None
    ):
        solar_self_consumed_energy_kwh = round(
            lifetime_solar_energy_kwh - lifetime_exported_energy_kwh,
            6,
        )
        if solar_self_consumed_energy_kwh < 0:
            _LOGGER.warning(
                "Derived solar self-consumed energy went negative; "
                "clamping to zero (solar=%s kWh, export=%s kWh)",
                lifetime_solar_energy_kwh,
                lifetime_exported_energy_kwh,
            )
            solar_self_consumed_energy_kwh = 0.0

    home_consumption_energy_kwh = None
    if (
        solar_self_consumed_energy_kwh is not None
        and lifetime_imported_energy_kwh is not None
    ):
        home_consumption_energy_kwh = round(
            solar_self_consumed_energy_kwh + lifetime_imported_energy_kwh,
            6,
        )
        if home_consumption_energy_kwh < 0:
            _LOGGER.warning(
                "Derived home consumption energy went negative; clamping to zero "
                "(solar_self_consumed=%s kWh, grid_import=%s kWh)",
                solar_self_consumed_energy_kwh,
                lifetime_imported_energy_kwh,
            )
            home_consumption_energy_kwh = 0.0

    home_load_power_w = None
    if dtu_power_w is not None and primary_meter is not None:
        import_w = primary_meter.grid_import_power_w or 0.0
        export_w = primary_meter.grid_export_power_w or 0.0
        home_load_power_w = round(dtu_power_w + import_w - export_w, 6)
        if home_load_power_w < 0:
            _LOGGER.warning(
                "Derived home load power went negative; clamping to zero "
                "(solar=%s W, grid_import=%s W, grid_export=%s W)",
                dtu_power_w,
                import_w,
                export_w,
            )
            home_load_power_w = 0.0

    return HoymilesSnapshot(
        dtu_serial=_serial(payload.get("deviceSerialNumber")),
        timestamp=_timestamp(payload.get("timestamp")),
        ap=_int(payload.get("ap")),
        cp=_int(payload.get("cp")),
        firmware_version=_int(payload.get("firmwareVersion")),
        dtu_power_w=dtu_power_w,
        dtu_daily_energy_kwh=dtu_daily_energy_kwh,
        lifetime_solar_energy_kwh=lifetime_solar_energy_kwh,
        solar_self_consumed_energy_kwh=solar_self_consumed_energy_kwh,
        home_consumption_energy_kwh=home_consumption_energy_kwh,
        home_load_power_w=home_load_power_w,
        meters=meters,
        inverters=inverters,
        mppts=mppts,
    )


def preserve_daily_energy_for_same_day(
    snapshot: HoymilesSnapshot,
    previous: HoymilesSnapshot | None,
    timezone: tzinfo,
) -> HoymilesSnapshot:
    """Keep daily energy from dropping to zero while devices sleep."""
    if previous is None or not _is_same_day(snapshot, previous, timezone):
        return snapshot

    previous_inverters = {item.serial: item for item in previous.inverters}
    previous_mppts = {
        (item.inverter_serial, item.port_number): item for item in previous.mppts
    }

    inverters = tuple(
        replace(
            inverter,
            daily_energy_kwh=_preserved_daily_energy(
                inverter.daily_energy_kwh,
                _previous_inverter_daily_energy(
                    previous_inverters,
                    inverter.serial,
                ),
            ),
        )
        for inverter in snapshot.inverters
    )
    mppts = tuple(
        replace(
            mppt,
            daily_energy_kwh=_preserved_daily_energy(
                mppt.daily_energy_kwh,
                _previous_mppt_daily_energy(
                    previous_mppts,
                    mppt.inverter_serial,
                    mppt.port_number,
                ),
            ),
        )
        for mppt in snapshot.mppts
    )

    return replace(
        snapshot,
        dtu_daily_energy_kwh=_preserved_daily_energy(
            snapshot.dtu_daily_energy_kwh,
            previous.dtu_daily_energy_kwh,
        ),
        inverters=inverters,
        mppts=mppts,
    )


def preserve_meter_lifetime_energy(
    snapshot: HoymilesSnapshot,
    previous: HoymilesSnapshot | None,
) -> HoymilesSnapshot:
    """Keep meter lifetime energy from dropping to zero during transient failures."""
    if previous is None:
        return snapshot

    previous_meters = {item.serial: item for item in previous.meters}
    meters = tuple(
        replace(
            meter,
            lifetime_imported_energy_kwh=_preserved_lifetime_energy(
                meter.lifetime_imported_energy_kwh,
                _previous_meter_lifetime_energy(
                    previous_meters,
                    meter.serial,
                    "lifetime_imported_energy_kwh",
                ),
            ),
            lifetime_exported_energy_kwh=_preserved_lifetime_energy(
                meter.lifetime_exported_energy_kwh,
                _previous_meter_lifetime_energy(
                    previous_meters,
                    meter.serial,
                    "lifetime_exported_energy_kwh",
                ),
            ),
        )
        for meter in snapshot.meters
    )

    return rebuild_meter_derived_energy(snapshot, meters)


def preserve_inverter_lifetime_energy(
    snapshot: HoymilesSnapshot,
    previous: HoymilesSnapshot | None,
) -> HoymilesSnapshot:
    """Keep inverter and MPPT lifetime energy from dropping to zero."""
    if previous is None:
        return snapshot

    previous_inverters = {item.serial: item for item in previous.inverters}
    previous_mppts = {
        (item.inverter_serial, item.port_number): item for item in previous.mppts
    }

    mppts = tuple(
        replace(
            mppt,
            lifetime_energy_kwh=_preserved_lifetime_energy(
                mppt.lifetime_energy_kwh,
                _previous_mppt_lifetime_energy(
                    previous_mppts,
                    mppt.inverter_serial,
                    mppt.port_number,
                ),
            ),
        )
        for mppt in snapshot.mppts
    )

    lifetime_by_inverter: dict[str, float] = {}
    for mppt in mppts:
        if mppt.lifetime_energy_kwh is None:
            continue
        lifetime_by_inverter[mppt.inverter_serial] = (
            lifetime_by_inverter.get(mppt.inverter_serial, 0.0)
            + mppt.lifetime_energy_kwh
        )

    total_lifetime_solar_energy_kwh = (
        round(sum(lifetime_by_inverter.values()), 6)
        if lifetime_by_inverter
        else None
    )

    inverters = tuple(
        replace(
            inverter,
            lifetime_energy_kwh=_restored_inverter_lifetime_energy(
                current=lifetime_by_inverter.get(inverter.serial),
                previous=_previous_inverter_lifetime_energy(
                    previous_inverters,
                    inverter.serial,
                ),
            ),
        )
        for inverter in snapshot.inverters
    )

    return replace(
        snapshot,
        lifetime_solar_energy_kwh=_restored_inverter_lifetime_energy(
            current=total_lifetime_solar_energy_kwh,
            previous=previous.lifetime_solar_energy_kwh,
        ),
        inverters=inverters,
        mppts=mppts,
    )


def rebuild_meter_derived_energy(
    snapshot: HoymilesSnapshot,
    meters: tuple[MeterData, ...],
) -> HoymilesSnapshot:
    """Recalculate meter-derived cumulative energy after meter preservation."""
    primary_meter = meters[0] if meters else None
    lifetime_imported_energy_kwh = (
        primary_meter.lifetime_imported_energy_kwh
        if primary_meter is not None
        else None
    )
    lifetime_exported_energy_kwh = (
        primary_meter.lifetime_exported_energy_kwh
        if primary_meter is not None
        else None
    )
    solar_self_consumed_energy_kwh = None
    if (
        snapshot.lifetime_solar_energy_kwh is not None
        and lifetime_exported_energy_kwh is not None
    ):
        solar_self_consumed_energy_kwh = round(
            snapshot.lifetime_solar_energy_kwh - lifetime_exported_energy_kwh,
            6,
        )
        if solar_self_consumed_energy_kwh < 0:
            _LOGGER.warning(
                "Derived solar self-consumed energy went negative; "
                "clamping to zero (solar=%s kWh, export=%s kWh)",
                snapshot.lifetime_solar_energy_kwh,
                lifetime_exported_energy_kwh,
            )
            solar_self_consumed_energy_kwh = 0.0

    home_consumption_energy_kwh = None
    if (
        solar_self_consumed_energy_kwh is not None
        and lifetime_imported_energy_kwh is not None
    ):
        home_consumption_energy_kwh = round(
            solar_self_consumed_energy_kwh + lifetime_imported_energy_kwh,
            6,
        )
        if home_consumption_energy_kwh < 0:
            _LOGGER.warning(
                "Derived home consumption energy went negative; clamping to zero "
                "(solar_self_consumed=%s kWh, grid_import=%s kWh)",
                solar_self_consumed_energy_kwh,
                lifetime_imported_energy_kwh,
            )
            home_consumption_energy_kwh = 0.0

    return replace(
        snapshot,
        meters=meters,
        solar_self_consumed_energy_kwh=solar_self_consumed_energy_kwh,
        home_consumption_energy_kwh=home_consumption_energy_kwh,
    )


def _is_same_day(
    snapshot: HoymilesSnapshot,
    previous: HoymilesSnapshot,
    timezone: tzinfo,
) -> bool:
    if snapshot.timestamp is None or previous.timestamp is None:
        return False
    return (
        snapshot.timestamp.astimezone(timezone).date()
        == previous.timestamp.astimezone(timezone).date()
    )


def _preserved_daily_energy(
    current: float | None,
    previous: float | None,
) -> float | None:
    if current not in (None, 0.0) or previous in (None, 0.0):
        return current
    return previous


def _previous_inverter_daily_energy(
    previous_inverters: Mapping[str, InverterData],
    serial: str,
) -> float | None:
    previous = previous_inverters.get(serial)
    return previous.daily_energy_kwh if previous is not None else None


def _previous_mppt_daily_energy(
    previous_mppts: Mapping[tuple[str, int], MpptData],
    inverter_serial: str,
    port_number: int,
) -> float | None:
    previous = previous_mppts.get((inverter_serial, port_number))
    return previous.daily_energy_kwh if previous is not None else None


def _preserved_lifetime_energy(
    current: float | None,
    previous: float | None,
) -> float | None:
    if current is not None and current > 0:
        return current
    if previous is not None and previous > 0:
        return previous
    return current


def _previous_meter_lifetime_energy(
    previous_meters: Mapping[str, MeterData],
    serial: str,
    attribute: str,
) -> float | None:
    previous = previous_meters.get(serial)
    if previous is None:
        return None
    return getattr(previous, attribute)


def _previous_inverter_lifetime_energy(
    previous_inverters: Mapping[str, InverterData],
    serial: str,
) -> float | None:
    previous = previous_inverters.get(serial)
    if previous is None:
        return None
    return previous.lifetime_energy_kwh


def _previous_mppt_lifetime_energy(
    previous_mppts: Mapping[tuple[str, int], MpptData],
    inverter_serial: str,
    port_number: int,
) -> float | None:
    previous = previous_mppts.get((inverter_serial, port_number))
    if previous is None:
        return None
    return previous.lifetime_energy_kwh


def _restored_inverter_lifetime_energy(
    current: float | None,
    previous: float | None,
) -> float | None:
    if current is not None and current > 0:
        return current
    if previous is not None and previous > 0:
        return previous
    return current


def _parse_meter(item: Mapping[str, Any]) -> MeterData:
    net_grid_power_w = _number(item.get("phaseTotalPower"), 0.1)
    grid_import_power_w = None
    grid_export_power_w = None
    if net_grid_power_w is not None:
        if net_grid_power_w < 0:
            grid_import_power_w = abs(net_grid_power_w)
            grid_export_power_w = 0.0
        else:
            grid_import_power_w = 0.0
            grid_export_power_w = net_grid_power_w

    return MeterData(
        serial=_serial(item.get("serialNumber")),
        device_type=_int(item.get("deviceType")),
        net_grid_power_w=net_grid_power_w,
        grid_import_power_w=grid_import_power_w,
        grid_export_power_w=grid_export_power_w,
        voltage_v=_number(item.get("voltagePhaseA"), 100),
        current_a=_number(item.get("currentPhaseA"), 100),
        power_factor=_number(item.get("powerFactorTotal"), 1000),
        lifetime_exported_energy_kwh=_number(item.get("energyTotalPower"), 100),
        lifetime_imported_energy_kwh=_number(
            item.get("energyTotalConsumed"), 100
        ),
        fault_code=_int(item.get("faultCode")),
    )


def _parse_inverter(
    item: Mapping[str, Any],
    daily_energy_by_serial: Mapping[str, float],
    lifetime_energy_by_serial: Mapping[str, float],
) -> InverterData:
    serial = _serial(item.get("serialNumber"))
    return InverterData(
        serial=serial,
        firmware_version=_int(item.get("firmwareVersion")),
        voltage_v=_number(item.get("voltage"), 10),
        frequency_hz=_number(item.get("frequency"), 100),
        active_power_w=_number(item.get("activePower"), 10),
        current_a=_number(item.get("current"), 100),
        power_factor=_number(item.get("powerFactor"), 1000),
        temperature_c=_number(item.get("temperature"), 10),
        warning_number=_int(item.get("warningNumber")),
        link_status=_int(item.get("linkStatus")),
        signal_dbm=_int(item.get("modulationIndexSignal")),
        daily_energy_kwh=round(daily_energy_by_serial[serial], 6)
        if serial in daily_energy_by_serial
        else None,
        lifetime_energy_kwh=round(lifetime_energy_by_serial[serial], 6)
        if serial in lifetime_energy_by_serial
        else None,
    )


def _parse_mppt(item: Mapping[str, Any]) -> MpptData:
    port_number = _int(item.get("portNumber"))
    if port_number is None:
        raise ValueError("MPPT payload is missing portNumber")

    return MpptData(
        inverter_serial=_serial(item.get("serialNumber")),
        port_number=port_number,
        voltage_v=_number(item.get("voltage"), 10),
        current_a=_number(item.get("current"), 100),
        power_w=_number(item.get("power"), 10),
        daily_energy_kwh=_number(item.get("energyDaily"), 1000),
        lifetime_energy_kwh=_number(item.get("energyTotal"), 1000),
        error_code=_int(item.get("errorCode")),
    )
