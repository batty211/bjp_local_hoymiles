from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "bjp_local_hoymiles"
PARSER_PATH = PACKAGE_ROOT / "parser.py"
INVERTER_LIFETIME_PATH = PACKAGE_ROOT / "inverter_lifetime.py"


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


def load_inverter_lifetime():
    parser = load_parser()
    _ensure_package("custom_components")
    _ensure_package("custom_components.bjp_local_hoymiles")
    spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.inverter_lifetime",
        INVERTER_LIFETIME_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, parser


def load_payload() -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "real_data_new.json").read_text())


def zero_inverter_lifetime_payload() -> dict:
    payload = load_payload()
    for mppt in payload["pvData"]:
        mppt["energyTotal"] = 0
    return payload


def test_restore_inverter_lifetime_cache_preserves_values_after_restart() -> None:
    inverter_lifetime, parser = load_inverter_lifetime()
    previous = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_inverter_lifetime_payload())
    cache = inverter_lifetime.InverterLifetimeCache(
        mppt_lifetime_energy_kwh={
            f"{mppt.inverter_serial}:{mppt.port_number}": mppt.lifetime_energy_kwh
            for mppt in previous.mppts
            if mppt.lifetime_energy_kwh is not None
        }
    )

    restored, updated_cache = inverter_lifetime.restore_inverter_lifetime_cache(
        current,
        cache,
    )

    assert restored.lifetime_solar_energy_kwh == 15665.132
    assert restored.inverters[0].lifetime_energy_kwh == 7844.197
    assert restored.mppts[0].lifetime_energy_kwh == 1962.413
    assert restored.solar_self_consumed_energy_kwh == 10300.852
    assert restored.home_consumption_energy_kwh == 29045.222
    assert updated_cache == cache


def test_restore_inverter_lifetime_cache_tracks_current_positive_values() -> None:
    inverter_lifetime, parser = load_inverter_lifetime()
    payload = load_payload()
    payload["pvData"][0]["energyTotal"] += 250
    current = parser.parse_snapshot(payload)
    cache = inverter_lifetime.InverterLifetimeCache(
        mppt_lifetime_energy_kwh={"19120000000001:1": 1962.413}
    )

    restored, updated_cache = inverter_lifetime.restore_inverter_lifetime_cache(
        current,
        cache,
    )

    assert restored.mppts[0].lifetime_energy_kwh == 1962.663
    assert restored.inverters[0].lifetime_energy_kwh == 7844.447
    assert restored.lifetime_solar_energy_kwh == 15665.382
    assert updated_cache is not None
    assert updated_cache.mppt_lifetime_energy_kwh["19120000000001:1"] == 1962.663
    assert len(updated_cache.mppt_lifetime_energy_kwh) == len(restored.mppts)


def test_inverter_lifetime_cache_round_trips_through_storage_format() -> None:
    inverter_lifetime, _ = load_inverter_lifetime()
    cache = inverter_lifetime.InverterLifetimeCache(
        mppt_lifetime_energy_kwh={"19120000000001:1": 1962.413}
    )

    restored = inverter_lifetime.deserialize_inverter_lifetime_cache(
        inverter_lifetime.serialize_inverter_lifetime_cache(cache)
    )

    assert restored == cache
