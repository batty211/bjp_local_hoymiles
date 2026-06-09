from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "bjp_local_hoymiles"
PARSER_PATH = PACKAGE_ROOT / "parser.py"
DAILY_ENERGY_PATH = PACKAGE_ROOT / "daily_energy.py"


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


def load_daily_energy():
    parser = load_parser()
    _ensure_package("custom_components")
    _ensure_package("custom_components.bjp_local_hoymiles")
    spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.daily_energy",
        DAILY_ENERGY_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, parser


def load_payload() -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "real_data_new.json").read_text())


def zero_daily_payload() -> dict:
    payload = load_payload()
    payload["dtuDailyEnergy"] = "0"
    for mppt in payload["pvData"]:
        mppt["energyDaily"] = 0
    return payload


def test_restore_daily_energy_cache_preserves_same_day_values_after_restart() -> None:
    daily_energy, parser = load_daily_energy()
    snapshot = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_daily_payload())
    cache = daily_energy.DailyEnergyCache(
        day=datetime.fromtimestamp(snapshot.timestamp.timestamp(), tz=UTC).date(),
        dtu_daily_energy_kwh=snapshot.dtu_daily_energy_kwh,
        inverter_daily_energy_kwh={
            inverter.serial: inverter.daily_energy_kwh
            for inverter in snapshot.inverters
            if inverter.daily_energy_kwh is not None
        },
        mppt_daily_energy_kwh={
            f"{mppt.inverter_serial}:{mppt.port_number}": mppt.daily_energy_kwh
            for mppt in snapshot.mppts
            if mppt.daily_energy_kwh is not None
        },
    )

    restored, updated_cache = daily_energy.restore_daily_energy_cache(
        current,
        cache,
        UTC,
    )

    assert restored.dtu_daily_energy_kwh == 10.62
    assert restored.inverters[0].daily_energy_kwh == 5.308
    assert restored.inverters[1].daily_energy_kwh == 5.312
    assert restored.mppts[0].daily_energy_kwh == 1.337
    assert updated_cache == cache


def test_restore_daily_energy_cache_handles_restart_with_no_previous_snapshot() -> None:
    daily_energy, parser = load_daily_energy()
    fixture_day = parser.parse_snapshot(load_payload()).timestamp.astimezone(UTC).date()
    current = parser.parse_snapshot(zero_daily_payload())
    cache = daily_energy.deserialize_daily_energy_cache(
        {
            "day": fixture_day.isoformat(),
            "dtu_daily_energy_kwh": 10.62,
            "inverter_daily_energy_kwh": {
                "19120000000001": 5.308,
                "19120000000002": 5.312,
            },
            "mppt_daily_energy_kwh": {
                "19120000000001:1": 1.337,
                "19120000000002:1": 1.331,
            },
        }
    )

    restored, updated_cache = daily_energy.restore_daily_energy_cache(
        current,
        cache,
        UTC,
    )

    assert restored.dtu_daily_energy_kwh == 10.62
    assert restored.inverters[0].daily_energy_kwh == 5.308
    assert restored.inverters[1].daily_energy_kwh == 5.312
    assert restored.mppts[0].daily_energy_kwh == 1.337
    assert updated_cache is not None
    assert updated_cache.day == fixture_day
    assert updated_cache.dtu_daily_energy_kwh == 10.62


def test_restore_daily_energy_cache_resets_on_next_day() -> None:
    daily_energy, parser = load_daily_energy()
    fixture_snapshot = parser.parse_snapshot(load_payload())
    current = parser.parse_snapshot(zero_daily_payload())
    current = parser.replace(
        current,
        timestamp=fixture_snapshot.timestamp + timedelta(days=1),
    )
    cache = daily_energy.deserialize_daily_energy_cache(
        {
            "day": fixture_snapshot.timestamp.astimezone(UTC).date().isoformat(),
            "dtu_daily_energy_kwh": 10.62,
            "inverter_daily_energy_kwh": {"19120000000001": 5.308},
            "mppt_daily_energy_kwh": {"19120000000001:1": 1.337},
        }
    )

    restored, updated_cache = daily_energy.restore_daily_energy_cache(
        current,
        cache,
        UTC,
    )

    assert restored.dtu_daily_energy_kwh == 0.0
    assert restored.inverters[0].daily_energy_kwh == 0.0
    assert restored.mppts[0].daily_energy_kwh == 0.0
    assert updated_cache is not None
    assert updated_cache.day == (
        fixture_snapshot.timestamp.astimezone(UTC).date() + timedelta(days=1)
    )
    assert updated_cache.dtu_daily_energy_kwh is None
    assert updated_cache.inverter_daily_energy_kwh == {}
    assert updated_cache.mppt_daily_energy_kwh == {}


def test_restore_daily_energy_cache_tracks_serials_and_ports_separately() -> None:
    daily_energy, parser = load_daily_energy()
    payload = zero_daily_payload()
    fixture_day = parser.parse_snapshot(load_payload()).timestamp.astimezone(UTC).date()

    current = parser.parse_snapshot(payload)
    cache = daily_energy.deserialize_daily_energy_cache(
        {
            "day": fixture_day.isoformat(),
            "dtu_daily_energy_kwh": 10.62,
            "inverter_daily_energy_kwh": {
                "19120000000001": 5.308,
                "19120000000002": 5.312,
            },
            "mppt_daily_energy_kwh": {
                "19120000000001:1": 1.337,
                "19120000000001:2": 1.314,
                "19120000000002:1": 1.331,
            },
        }
    )

    restored, _ = daily_energy.restore_daily_energy_cache(current, cache, UTC)

    assert restored.inverters[0].daily_energy_kwh == 5.308
    assert restored.inverters[1].daily_energy_kwh == 5.312
    assert restored.mppts[0].daily_energy_kwh == 1.337
    assert restored.mppts[1].daily_energy_kwh == 1.314
    assert restored.mppts[4].daily_energy_kwh == 1.331


def test_daily_energy_cache_round_trips_through_storage_format() -> None:
    daily_energy, _ = load_daily_energy()
    cache = daily_energy.DailyEnergyCache(
        day=datetime(2026, 6, 9, tzinfo=UTC).date(),
        dtu_daily_energy_kwh=10.62,
        inverter_daily_energy_kwh={"19120000000001": 5.308},
        mppt_daily_energy_kwh={"19120000000001:1": 1.337},
    )

    restored = daily_energy.deserialize_daily_energy_cache(
        daily_energy.serialize_daily_energy_cache(cache)
    )

    assert restored == cache
