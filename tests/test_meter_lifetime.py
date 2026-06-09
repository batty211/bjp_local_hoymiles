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

    assert restored.meters[0].lifetime_imported_energy_kwh == 1874.437
    assert restored.meters[0].lifetime_exported_energy_kwh == 536.428
    assert restored.solar_self_consumed_energy_kwh == 15128.704
    assert restored.home_consumption_energy_kwh == 17003.141
    assert updated_cache == cache


def test_restore_meter_lifetime_cache_tracks_current_positive_values() -> None:
    meter_lifetime, parser = load_meter_lifetime()
    payload = load_payload()
    payload["meterData"][0]["energyTotalConsumed"] = 1877719
    payload["meterData"][0]["energyTotalPower"] = 536430
    current = parser.parse_snapshot(payload)
    cache = meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 1874.437},
        meter_lifetime_exported_energy_kwh={"18410000000001": 536.428},
    )

    restored, updated_cache = meter_lifetime.restore_meter_lifetime_cache(
        current,
        cache,
    )

    assert restored.meters[0].lifetime_imported_energy_kwh == 1877.719
    assert restored.meters[0].lifetime_exported_energy_kwh == 536.43
    assert updated_cache == meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 1877.719},
        meter_lifetime_exported_energy_kwh={"18410000000001": 536.43},
    )


def test_meter_lifetime_cache_round_trips_through_storage_format() -> None:
    meter_lifetime, _ = load_meter_lifetime()
    cache = meter_lifetime.MeterLifetimeCache(
        meter_lifetime_imported_energy_kwh={"18410000000001": 1874.437},
        meter_lifetime_exported_energy_kwh={"18410000000001": 536.428},
    )

    restored = meter_lifetime.deserialize_meter_lifetime_cache(
        meter_lifetime.serialize_meter_lifetime_cache(cache)
    )

    assert restored == cache
