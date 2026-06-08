"""Payload parser for Hoymiles DTU real-time data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


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
    home_load_power_w = None
    if dtu_power_w is not None and primary_meter is not None:
        import_w = primary_meter.grid_import_power_w or 0.0
        export_w = primary_meter.grid_export_power_w or 0.0
        home_load_power_w = round(dtu_power_w + import_w - export_w, 6)

    return HoymilesSnapshot(
        dtu_serial=_serial(payload.get("deviceSerialNumber")),
        timestamp=_timestamp(payload.get("timestamp")),
        ap=_int(payload.get("ap")),
        cp=_int(payload.get("cp")),
        firmware_version=_int(payload.get("firmwareVersion")),
        dtu_power_w=dtu_power_w,
        dtu_daily_energy_kwh=dtu_daily_energy_kwh,
        lifetime_solar_energy_kwh=lifetime_solar_energy_kwh,
        home_load_power_w=home_load_power_w,
        meters=meters,
        inverters=inverters,
        mppts=mppts,
    )


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
        lifetime_exported_energy_kwh=_number(item.get("energyTotalPower"), 1000),
        lifetime_imported_energy_kwh=_number(
            item.get("energyTotalConsumed"), 1000
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
