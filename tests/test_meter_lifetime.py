from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "bjp_local_hoymiles"
PARSER_PATH = PACKAGE_ROOT / "parser.py"
METER_LIFETIME_PATH = PACKAGE_ROOT / "meter_lifetime.py"


def _ensure_package(name: str) -> types.ModuleType:
    package = sys.modules.get(name)
    if package is not None:
        return package
    package = types.ModuleType(name)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    sys.modules[name] = package
    return package


def load_parser():
    _ensure_package("custom_components")
    _ensure_package("custom_components.bjp_local_hoymiles")
    spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.parser",
        PARSER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_meter_lifetime():
    parser = load_parser()
    _ensure_package("custom_components")
    _ensure_package("custom_components.bjp_local_hoymiles")
    spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.meter_lifetime",
        METER_LIFETIME_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, parser


def load_payload() -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "real_data_new.json").read_text())


def zero_meter_payload() -> dict:
    payload = load_payload()
    meter = payload["meterData"][0]
    meter["energyTotalConsumed"] = 0
    meter["energyTotalPower"] = 0
    return payload


def test_restore_meter_lifetime_cache_preserves_values_after_restart() -> None:
    meter_lifetime, parser = load_meter_lifetime()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_meter_payload())
    cache = meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={
            meter.serial: meter.lifetime_imported_energy_kwh
            for meter in previous.meters
            if meter.lifetime_imported_energy_kwh is not None
        },
        meter_lifetime_exported_energy_kwh={
            meter.serial: meter.lifetime_exported_energy_kwh
            for meter in previous.meters
            if meter.lifetime_exported_energy_kwh is not None
        },
    )

    restored, updated_cache = meter_lifetime.restore_meter_lifetime_cache(
        current,
        cache,
    )

    assert restored.meters[0].lifetime_imported_energy_kwh == 18744.37
    assert restored.meters[0].lifetime_exported_energy_kwh == 5364.28
    assert restored.solar_self_consumed_energy_kwh == 10300.852
    assert restored.home_consumption_energy_kwh == 29045.222
    assert updated_cache == cache


def test_restore_meter_lifetime_cache_tracks_current_positive_values() -> None:
    meter_lifetime, parser = load_meter_lifetime()
    payload = load_payload()
    payload["meterData"][0]["energyTotalConsumed"] = 1877719
    payload["meterData"][0]["energyTotalPower"] = 536430
    current = parser.parse_snapshot(payload)
    cache = meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 18744.37},
        meter_lifetime_exported_energy_kwh={"18410000000001": 5364.28},
    )

    restored, updated_cache = meter_lifetime.restore_meter_lifetime_cache(
        current,
        cache,
    )

    assert restored.meters[0].lifetime_imported_energy_kwh == 18777.19
    assert restored.meters[0].lifetime_exported_energy_kwh == 5364.3
    assert updated_cache == meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 18777.19},
        meter_lifetime_exported_energy_kwh={"18410000000001": 5364.3},
    )


def test_meter_lifetime_cache_round_trips_through_storage_format() -> None:
    meter_lifetime, _ = load_meter_lifetime()
    cache = meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 18744.37},
        meter_lifetime_exported_energy_kwh={"18410000000001": 5364.28},
    )

    restored = meter_lifetime.deserialize_meter_lifetime_cache(
        meter_lifetime.serialize_meter_lifetime_cache(cache)
    )

    assert restored == cache


def test_meter_lifetime_cache_migrates_legacy_scale_once() -> None:
    meter_lifetime, _ = load_meter_lifetime()

    migrated = meter_lifetime.deserialize_meter_lifetime_cache(
        {
            "meter_lifetime_imported_energy_kwh": {
                "18410000000001": 1878.897
            },
            "meter_lifetime_exported_energy_kwh": {
                "18410000000001": 536.84
            },
        }
    )

    assert migrated == meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 18788.97},
        meter_lifetime_exported_energy_kwh={"18410000000001": 5368.4},
    )
    assert meter_lifetime.meter_lifetime_cache_needs_migration(
        {
            "meter_lifetime_imported_energy_kwh": {
                "18410000000001": 1878.897
            }
        }
    )

    serialized = meter_lifetime.serialize_meter_lifetime_cache(migrated)
    assert serialized["format_version"] == meter_lifetime.CACHE_FORMAT_VERSION
    assert not meter_lifetime.meter_lifetime_cache_needs_migration(serialized)
    assert meter_lifetime.deserialize_meter_lifetime_cache(serialized) == migrated


def test_legacy_cache_restores_correct_scale_on_zero_first_poll() -> None:
    meter_lifetime, parser = load_meter_lifetime()
    current = parser.parse_snapshot(zero_meter_payload())
    migrated = meter_lifetime.deserialize_meter_lifetime_cache(
        {
            "meter_lifetime_imported_energy_kwh": {
                "18410000000001": 1874.437
            },
            "meter_lifetime_exported_energy_kwh": {
                "18410000000001": 536.428
            },
        }
    )

    restored, _ = meter_lifetime.restore_meter_lifetime_cache(current, migrated)

    assert restored.meters[0].lifetime_imported_energy_kwh == 18744.37
    assert restored.meters[0].lifetime_exported_energy_kwh == 5364.28
    assert restored.solar_self_consumed_energy_kwh == 10300.852
    assert restored.home_consumption_energy_kwh == 29045.222
