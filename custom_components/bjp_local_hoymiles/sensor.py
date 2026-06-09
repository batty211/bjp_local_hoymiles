"""Sensor platform for BJP Local Hoymiles."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_INVERTER_SERIAL,
    ATTR_PORT_NUMBER,
    DOMAIN,
    MANUFACTURER,
    MODEL_DTU_PRO_S,
    MODEL_METER_DDSU666,
)
from .coordinator import BjpLocalHoymilesCoordinator
from .parser import HoymilesSnapshot, InverterData, MeterData, MpptData

ValueFn = Callable[[HoymilesSnapshot], Any]


@dataclass(frozen=True, kw_only=True)
class HoymilesSensorDescription(SensorEntityDescription):
    """Description for a Hoymiles sensor."""

    value_fn: ValueFn
    device_key: str
    attr_fn: Callable[[HoymilesSnapshot], dict[str, Any]] | None = None


def _energy_description(
    key: str,
    translation_key: str,
    value_fn: ValueFn,
    device_key: str,
    state_class: SensorStateClass = SensorStateClass.TOTAL_INCREASING,
    enabled: bool = True,
    translation_placeholders: dict[str, str] | None = None,
) -> HoymilesSensorDescription:
    return HoymilesSensorDescription(
        key=key,
        translation_key=translation_key,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=state_class,
        value_fn=value_fn,
        device_key=device_key,
        entity_registry_enabled_default=enabled,
        translation_placeholders=translation_placeholders,
    )


def _measurement_description(
    key: str,
    translation_key: str,
    value_fn: ValueFn,
    device_key: str,
    unit: str | None = None,
    device_class: SensorDeviceClass | None = None,
    enabled: bool = True,
    translation_placeholders: dict[str, str] | None = None,
) -> HoymilesSensorDescription:
    return HoymilesSensorDescription(
        key=key,
        translation_key=translation_key,
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=value_fn,
        device_key=device_key,
        entity_registry_enabled_default=enabled,
        translation_placeholders=translation_placeholders,
    )


DTU_DESCRIPTIONS: tuple[HoymilesSensorDescription, ...] = (
    _measurement_description(
        "solar_power",
        "solar_power",
        lambda data: data.dtu_power_w,
        "dtu",
        UnitOfPower.WATT,
        SensorDeviceClass.POWER,
    ),
    _energy_description(
        "daily_solar_energy",
        "daily_solar_energy",
        lambda data: data.dtu_daily_energy_kwh,
        "dtu",
    ),
    _energy_description(
        "lifetime_solar_energy",
        "lifetime_solar_energy",
        lambda data: data.lifetime_solar_energy_kwh,
        "dtu",
        SensorStateClass.TOTAL,
    ),
    _energy_description(
        "solar_self_consumed_energy",
        "solar_self_consumed_energy",
        lambda data: data.solar_self_consumed_energy_kwh,
        "dtu",
        SensorStateClass.TOTAL,
    ),
    _energy_description(
        "home_consumption_energy",
        "home_consumption_energy",
        lambda data: data.home_consumption_energy_kwh,
        "dtu",
        SensorStateClass.TOTAL,
    ),
    _measurement_description(
        "home_load_power",
        "home_load_power",
        lambda data: data.home_load_power_w,
        "dtu",
        UnitOfPower.WATT,
        SensorDeviceClass.POWER,
    ),
    HoymilesSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.timestamp,
        device_key="dtu",
    ),
    HoymilesSensorDescription(
        key="connection_status",
        translation_key="connection_status",
        device_class=SensorDeviceClass.ENUM,
        options=["online", "unavailable"],
        value_fn=lambda data: "online",
        device_key="dtu",
    ),
    HoymilesSensorDescription(
        key="firmware_raw",
        translation_key="firmware_raw",
        value_fn=lambda data: data.firmware_version,
        device_key="dtu",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HoymilesSensorDescription(
        key="ap",
        translation_key="ap",
        value_fn=lambda data: data.ap,
        device_key="dtu",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HoymilesSensorDescription(
        key="cp",
        translation_key="cp",
        value_fn=lambda data: data.cp,
        device_key="dtu",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BJP Local Hoymiles sensors."""
    coordinator: BjpLocalHoymilesCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_device_keys: set[str] = set()

    def add_new_entities() -> None:
        entities: list[SensorEntity] = []
        snapshot = coordinator.data
        if snapshot is None:
            return

        if "dtu" not in known_device_keys:
            entities.extend(
                BjpLocalHoymilesSensor(coordinator, description)
                for description in DTU_DESCRIPTIONS
            )
            known_device_keys.add("dtu")

        for index, meter in enumerate(snapshot.meters):
            device_key = f"meter_{meter.serial}"
            if device_key not in known_device_keys:
                entities.extend(_meter_entities(coordinator, meter, index))
                known_device_keys.add(device_key)

        for inverter in snapshot.inverters:
            device_key = f"inverter_{inverter.serial}"
            if device_key not in known_device_keys:
                entities.extend(_inverter_entities(coordinator, inverter))
                known_device_keys.add(device_key)

        known_mppts = {
            key for key in known_device_keys if key.startswith("mppt_")
        }
        for mppt in snapshot.mppts:
            mppt_key = f"mppt_{mppt.inverter_serial}_{mppt.port_number}"
            if mppt_key not in known_mppts:
                entities.extend(_mppt_entities(coordinator, mppt))
                known_device_keys.add(mppt_key)

        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class BjpLocalHoymilesSensor(
    CoordinatorEntity[BjpLocalHoymilesCoordinator],
    SensorEntity,
):
    """BJP Local Hoymiles sensor entity."""

    entity_description: HoymilesSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BjpLocalHoymilesCoordinator,
        description: HoymilesSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.unique_id}_{description.device_key}_"
            f"{description.key}"
        )
        self._attr_device_info = _device_info(coordinator.data, description.device_key)

    @property
    def native_value(self) -> float | int | str | datetime | None:
        """Return the native value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.last_update_success and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)


def _meter_entities(
    coordinator: BjpLocalHoymilesCoordinator,
    meter: MeterData,
    index: int,
) -> list[BjpLocalHoymilesSensor]:
    device_key = f"meter_{meter.serial}"

    def select(data: HoymilesSnapshot) -> MeterData | None:
        return next((item for item in data.meters if item.serial == meter.serial), None)

    descriptions = (
        _measurement_description(
            f"{meter.serial}_grid_import_power",
            "grid_import_power",
            lambda data: (m.grid_import_power_w if (m := select(data)) else None),
            device_key,
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
        ),
        _measurement_description(
            f"{meter.serial}_grid_export_power",
            "grid_export_power",
            lambda data: (m.grid_export_power_w if (m := select(data)) else None),
            device_key,
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
        ),
        _measurement_description(
            f"{meter.serial}_net_grid_power",
            "net_grid_power",
            lambda data: (m.net_grid_power_w if (m := select(data)) else None),
            device_key,
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
        ),
        _measurement_description(
            f"{meter.serial}_voltage",
            "voltage",
            lambda data: (m.voltage_v if (m := select(data)) else None),
            device_key,
            UnitOfElectricPotential.VOLT,
            SensorDeviceClass.VOLTAGE,
        ),
        _measurement_description(
            f"{meter.serial}_current",
            "current",
            lambda data: (m.current_a if (m := select(data)) else None),
            device_key,
            UnitOfElectricCurrent.AMPERE,
            SensorDeviceClass.CURRENT,
        ),
        _measurement_description(
            f"{meter.serial}_power_factor",
            "power_factor",
            lambda data: (m.power_factor if (m := select(data)) else None),
            device_key,
        ),
        _energy_description(
            f"{meter.serial}_lifetime_imported_energy",
            "lifetime_imported_energy",
            lambda data: (
                m.lifetime_imported_energy_kwh if (m := select(data)) else None
            ),
            device_key,
            SensorStateClass.TOTAL,
        ),
        _energy_description(
            f"{meter.serial}_lifetime_exported_energy",
            "lifetime_exported_energy",
            lambda data: (
                m.lifetime_exported_energy_kwh if (m := select(data)) else None
            ),
            device_key,
            SensorStateClass.TOTAL,
        ),
        HoymilesSensorDescription(
            key=f"{meter.serial}_fault_code",
            translation_key="fault_code",
            value_fn=lambda data: (m.fault_code if (m := select(data)) else None),
            device_key=device_key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
    )
    return [
        BjpLocalHoymilesSensor(coordinator, description)
        for description in descriptions
    ]


def _inverter_entities(
    coordinator: BjpLocalHoymilesCoordinator,
    inverter: InverterData,
) -> list[BjpLocalHoymilesSensor]:
    device_key = f"inverter_{inverter.serial}"

    def select(data: HoymilesSnapshot) -> InverterData | None:
        return next(
            (item for item in data.inverters if item.serial == inverter.serial),
            None,
        )

    descriptions = (
        _measurement_description(
            f"{inverter.serial}_active_power",
            "active_power",
            lambda data: (i.active_power_w if (i := select(data)) else None),
            device_key,
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
        ),
        _energy_description(
            f"{inverter.serial}_daily_energy",
            "daily_energy",
            lambda data: (i.daily_energy_kwh if (i := select(data)) else None),
            device_key,
        ),
        _energy_description(
            f"{inverter.serial}_lifetime_energy",
            "lifetime_energy",
            lambda data: (i.lifetime_energy_kwh if (i := select(data)) else None),
            device_key,
            SensorStateClass.TOTAL,
        ),
        _measurement_description(
            f"{inverter.serial}_voltage",
            "voltage",
            lambda data: (i.voltage_v if (i := select(data)) else None),
            device_key,
            UnitOfElectricPotential.VOLT,
            SensorDeviceClass.VOLTAGE,
        ),
        _measurement_description(
            f"{inverter.serial}_current",
            "current",
            lambda data: (i.current_a if (i := select(data)) else None),
            device_key,
            UnitOfElectricCurrent.AMPERE,
            SensorDeviceClass.CURRENT,
        ),
        _measurement_description(
            f"{inverter.serial}_power_factor",
            "power_factor",
            lambda data: (i.power_factor if (i := select(data)) else None),
            device_key,
        ),
        _measurement_description(
            f"{inverter.serial}_temperature",
            "temperature",
            lambda data: (i.temperature_c if (i := select(data)) else None),
            device_key,
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
        ),
        HoymilesSensorDescription(
            key=f"{inverter.serial}_link_status",
            translation_key="link_status",
            device_class=SensorDeviceClass.ENUM,
            options=["online", "offline", "unknown"],
            value_fn=lambda data: _link_status(select(data)),
            device_key=device_key,
        ),
        _measurement_description(
            f"{inverter.serial}_frequency",
            "frequency",
            lambda data: (i.frequency_hz if (i := select(data)) else None),
            device_key,
            UnitOfFrequency.HERTZ,
            SensorDeviceClass.FREQUENCY,
            enabled=False,
        ),
        _measurement_description(
            f"{inverter.serial}_signal_strength",
            "signal_strength",
            lambda data: (i.signal_dbm if (i := select(data)) else None),
            device_key,
            "dBm",
            SensorDeviceClass.SIGNAL_STRENGTH,
            enabled=False,
        ),
        HoymilesSensorDescription(
            key=f"{inverter.serial}_warning_number",
            translation_key="warning_number",
            value_fn=lambda data: (i.warning_number if (i := select(data)) else None),
            device_key=device_key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        HoymilesSensorDescription(
            key=f"{inverter.serial}_firmware_raw",
            translation_key="firmware_raw",
            value_fn=lambda data: (
                i.firmware_version if (i := select(data)) else None
            ),
            device_key=device_key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
    )
    return [
        BjpLocalHoymilesSensor(coordinator, description)
        for description in descriptions
    ]


def _mppt_entities(
    coordinator: BjpLocalHoymilesCoordinator,
    mppt: MpptData,
) -> list[BjpLocalHoymilesSensor]:
    device_key = f"inverter_{mppt.inverter_serial}"

    def select(data: HoymilesSnapshot) -> MpptData | None:
        return next(
            (
                item
                for item in data.mppts
                if item.inverter_serial == mppt.inverter_serial
                and item.port_number == mppt.port_number
            ),
            None,
        )

    prefix = f"{mppt.inverter_serial}_mppt_{mppt.port_number}"
    placeholders = {"port": str(mppt.port_number)}
    descriptions = (
        _measurement_description(
            f"{prefix}_power",
            "mppt_power",
            lambda data: (p.power_w if (p := select(data)) else None),
            device_key,
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
            translation_placeholders=placeholders,
        ),
        _measurement_description(
            f"{prefix}_voltage",
            "mppt_voltage",
            lambda data: (p.voltage_v if (p := select(data)) else None),
            device_key,
            UnitOfElectricPotential.VOLT,
            SensorDeviceClass.VOLTAGE,
            translation_placeholders=placeholders,
        ),
        _measurement_description(
            f"{prefix}_current",
            "mppt_current",
            lambda data: (p.current_a if (p := select(data)) else None),
            device_key,
            UnitOfElectricCurrent.AMPERE,
            SensorDeviceClass.CURRENT,
            translation_placeholders=placeholders,
        ),
        _energy_description(
            f"{prefix}_daily_energy",
            "mppt_daily_energy",
            lambda data: (p.daily_energy_kwh if (p := select(data)) else None),
            device_key,
            enabled=False,
            translation_placeholders=placeholders,
        ),
        _energy_description(
            f"{prefix}_lifetime_energy",
            "mppt_lifetime_energy",
            lambda data: (p.lifetime_energy_kwh if (p := select(data)) else None),
            device_key,
            SensorStateClass.TOTAL,
            enabled=False,
            translation_placeholders=placeholders,
        ),
        HoymilesSensorDescription(
            key=f"{prefix}_error_code",
            translation_key="error_code",
            value_fn=lambda data: (p.error_code if (p := select(data)) else None),
            device_key=device_key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            translation_placeholders=placeholders,
            attr_fn=lambda data: {
                ATTR_INVERTER_SERIAL: mppt.inverter_serial,
                ATTR_PORT_NUMBER: mppt.port_number,
            },
        ),
    )
    return [
        BjpLocalHoymilesSensor(coordinator, description)
        for description in descriptions
    ]


def _link_status(inverter: InverterData | None) -> str | None:
    if inverter is None:
        return None
    if inverter.link_status == 1:
        return "online"
    if inverter.link_status == 0:
        return "offline"
    return "unknown"


def _device_info(snapshot: HoymilesSnapshot, device_key: str) -> DeviceInfo:
    if device_key == "dtu":
        return DeviceInfo(
            identifiers={(DOMAIN, snapshot.dtu_serial)},
            name="BJP Local Hoymiles DTU",
            manufacturer=MANUFACTURER,
            model=MODEL_DTU_PRO_S,
            serial_number=snapshot.dtu_serial,
        )

    if device_key.startswith("meter_"):
        serial = device_key.removeprefix("meter_")
        return DeviceInfo(
            identifiers={(DOMAIN, f"{snapshot.dtu_serial}_{serial}")},
            name=f"Hoymiles Meter {serial}",
            manufacturer=MANUFACTURER,
            model=MODEL_METER_DDSU666,
            serial_number=serial,
            via_device=(DOMAIN, snapshot.dtu_serial),
        )

    serial = device_key.removeprefix("inverter_")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{snapshot.dtu_serial}_{serial}")},
        name=f"Hoymiles Inverter {serial}",
        manufacturer=MANUFACTURER,
        serial_number=serial,
        via_device=(DOMAIN, snapshot.dtu_serial),
    )
