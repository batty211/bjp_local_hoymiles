from __future__ import annotations

import importlib.util
import json
import logging
import sys
from contextlib import contextmanager
from datetime import UTC
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "real_data_new.json"
PARSER = (
    Path(__file__).parents[1]
    / "custom_components"
    / "bjp_local_hoymiles"
    / "parser.py"
)


def load_parser():
    spec = importlib.util.spec_from_file_location("bjp_local_hoymiles_parser", PARSER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_payload() -> dict:
    return json.loads(FIXTURE.read_text())


def zero_daily_payload() -> dict:
    payload = load_payload()
    payload["dtuDailyEnergy"] = "0"
    for mppt in payload["pvData"]:
        mppt["energyDaily"] = 0
    return payload


def zero_meter_payload() -> dict:
    payload = load_payload()
    meter = payload["meterData"][0]
    meter["energyTotalConsumed"] = 0
    meter["energyTotalPower"] = 0
    return payload


@contextmanager
def capture_parser_warnings() -> list[str]:
    logger = logging.getLogger("bjp_local_hoymiles_parser")
    messages: list[str] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    handler = _Handler()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    try:
        yield messages
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def test_parse_snapshot_scales_payload_values() -> None:
    snapshot = load_parser().parse_snapshot(load_payload())

    assert snapshot.dtu_serial == "4121TEST0001"
    assert snapshot.dtu_power_w == 227.1
    assert snapshot.dtu_daily_energy_kwh == 10.62
    assert snapshot.lifetime_solar_energy_kwh == 15665.132
    assert snapshot.solar_self_consumed_energy_kwh == 15128.704
    assert snapshot.home_consumption_energy_kwh == 17003.141
    assert len(snapshot.meters) == 1
    assert len(snapshot.inverters) == 2
    assert len(snapshot.mppts) == 8

    meter = snapshot.meters[0]
    assert meter.net_grid_power_w == -1770.0
    assert meter.grid_import_power_w == 1770.0
    assert meter.grid_export_power_w == 0.0
    assert meter.voltage_v == 228.0
    assert meter.current_a == 8.85
    assert meter.power_factor == -0.938
    assert meter.lifetime_exported_energy_kwh == 536.428
    assert meter.lifetime_imported_energy_kwh == 1874.437

    assert snapshot.home_load_power_w == 1997.1


def test_parse_snapshot_clamps_negative_derived_energy() -> None:
    payload = load_payload()
    payload["meterData"][0]["energyTotalPower"] = 20_000_000

    with capture_parser_warnings() as messages:
        snapshot = load_parser().parse_snapshot(payload)

    assert snapshot.solar_self_consumed_energy_kwh == 0.0
    assert snapshot.home_consumption_energy_kwh == 1874.437
    assert any(
        "solar self-consumed energy went negative" in message
        for message in messages
    )


def test_parse_snapshot_clamps_negative_home_load_power() -> None:
    payload = load_payload()
    payload["meterData"][0]["phaseTotalPower"] = 30_000
    payload["meterData"][0]["phaseAPower"] = 30_000

    with capture_parser_warnings() as messages:
        snapshot = load_parser().parse_snapshot(payload)

    assert snapshot.home_load_power_w == 0.0
    assert any("home load power went negative" in message for message in messages)


def test_parse_snapshot_uses_mppt_daily_energy_when_dtu_reports_zero() -> None:
    payload = load_payload()
    payload["dtuDailyEnergy"] = "0"

    snapshot = load_parser().parse_snapshot(payload)

    assert snapshot.dtu_daily_energy_kwh == 10.62


def test_parse_snapshot_uses_mppt_daily_energy_when_dtu_value_is_missing() -> None:
    payload = load_payload()
    payload.pop("dtuDailyEnergy")

    snapshot = load_parser().parse_snapshot(payload)

    assert snapshot.dtu_daily_energy_kwh == 10.62


def test_preserve_daily_energy_keeps_same_day_values() -> None:
    parser = load_parser()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_daily_payload())

    snapshot = parser.preserve_daily_energy_for_same_day(
        current,
        previous,
        UTC,
    )

    assert snapshot.dtu_daily_energy_kwh == 10.62
    assert snapshot.inverters[0].daily_energy_kwh == 5.308
    assert snapshot.inverters[1].daily_energy_kwh == 5.312
    assert snapshot.mppts[0].daily_energy_kwh == 1.337


def test_preserve_daily_energy_allows_next_day_reset() -> None:
    payload = zero_daily_payload()
    payload["timestamp"] = payload["timestamp"] + 86400
    parser = load_parser()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(payload)

    snapshot = parser.preserve_daily_energy_for_same_day(
        current,
        previous,
        UTC,
    )

    assert snapshot.dtu_daily_energy_kwh == 0.0
    assert snapshot.inverters[0].daily_energy_kwh == 0.0
    assert snapshot.mppts[0].daily_energy_kwh == 0.0


def test_preserve_meter_lifetime_keeps_same_serial_values() -> None:
    parser = load_parser()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_meter_payload())

    snapshot = parser.preserve_meter_lifetime_energy(current, previous)

    assert snapshot.meters[0].lifetime_imported_energy_kwh == 1874.437
    assert snapshot.meters[0].lifetime_exported_energy_kwh == 536.428
    assert snapshot.solar_self_consumed_energy_kwh == 15128.704
    assert snapshot.home_consumption_energy_kwh == 17003.141


def test_preserve_meter_lifetime_uses_current_positive_values() -> None:
    payload = load_payload()
    payload["meterData"][0]["energyTotalConsumed"] = 1877719
    payload["meterData"][0]["energyTotalPower"] = 536430
    parser = load_parser()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(payload)

    snapshot = parser.preserve_meter_lifetime_energy(current, previous)

    assert snapshot.meters[0].lifetime_imported_energy_kwh == 1877.719
    assert snapshot.meters[0].lifetime_exported_energy_kwh == 536.43


def test_preserve_meter_lifetime_tracks_serials_separately() -> None:
    payload = load_payload()
    payload["meterData"] = [
        {
            **payload["meterData"][0],
            "serialNumber": "18417181655590",
            "energyTotalConsumed": 0,
            "energyTotalPower": 0,
        },
        {
            **payload["meterData"][0],
            "serialNumber": "18417181655591",
            "energyTotalConsumed": 0,
            "energyTotalPower": 0,
        },
    ]

    previous_payload = load_payload()
    previous_payload["meterData"] = [
        {
            **previous_payload["meterData"][0],
            "serialNumber": "18417181655590",
            "energyTotalConsumed": 1877437,
            "energyTotalPower": 536428,
        },
        {
            **previous_payload["meterData"][0],
            "serialNumber": "18417181655592",
            "energyTotalConsumed": 1999000,
            "energyTotalPower": 123456,
        },
    ]

    parser = load_parser()
    previous = parser.parse_snapshot(previous_payload)
    current = parser.parse_snapshot(payload)

    snapshot = parser.preserve_meter_lifetime_energy(current, previous)

    assert snapshot.meters[0].serial == "18417181655590"
    assert snapshot.meters[0].lifetime_imported_energy_kwh == 1877.437
    assert snapshot.meters[0].lifetime_exported_energy_kwh == 536.428
    assert snapshot.meters[1].serial == "18417181655591"
    assert snapshot.meters[1].lifetime_imported_energy_kwh == 0.0
    assert snapshot.meters[1].lifetime_exported_energy_kwh == 0.0


def test_preserve_meter_lifetime_keeps_derived_energy_from_bouncing() -> None:
    parser = load_parser()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_meter_payload())

    snapshot = parser.preserve_meter_lifetime_energy(current, previous)

    assert snapshot.solar_self_consumed_energy_kwh == 15128.704
    assert snapshot.home_consumption_energy_kwh == 17003.141


def test_parse_snapshot_groups_mppt_energy_by_inverter() -> None:
    snapshot = load_parser().parse_snapshot(load_payload())

    first = snapshot.inverters[0]
    second = snapshot.inverters[1]

    assert first.daily_energy_kwh == 5.308
    assert first.lifetime_energy_kwh == 7844.197
    assert first.active_power_w == 113.9
    assert first.voltage_v == 228.7
    assert first.frequency_hz == 49.96
    assert first.current_a == 0.49
    assert first.power_factor == 1.0
    assert first.temperature_c == 35.0
    assert first.signal_dbm == -68

    assert second.daily_energy_kwh == 5.312
    assert second.lifetime_energy_kwh == 7820.935


def test_parse_snapshot_scales_mppt_values() -> None:
    snapshot = load_parser().parse_snapshot(load_payload())
    mppt = snapshot.mppts[0]

    assert mppt.inverter_serial == "19120000000001"
    assert mppt.port_number == 1
    assert mppt.voltage_v == 38.5
    assert mppt.current_a == 0.78
    assert mppt.power_w == 30.2
    assert mppt.daily_energy_kwh == 1.337
    assert mppt.lifetime_energy_kwh == 1962.413
