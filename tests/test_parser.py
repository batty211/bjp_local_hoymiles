from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys

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


def test_parse_snapshot_scales_payload_values() -> None:
    snapshot = load_parser().parse_snapshot(load_payload())

    assert snapshot.dtu_serial == "4121TEST0001"
    assert snapshot.dtu_power_w == 227.1
    assert snapshot.dtu_daily_energy_kwh == 10.62
    assert snapshot.lifetime_solar_energy_kwh == 15665.132
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
