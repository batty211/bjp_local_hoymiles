#!/usr/bin/env python3
"""Read-only terminal monitor for BJP Local Hoymiles."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
PARSER_PATH = (
    ROOT / "custom_components" / "bjp_local_hoymiles" / "parser.py"
)
DEFAULT_PORT = 10081
DEFAULT_INTERVAL = 35
DEFAULT_TIMEOUT = 10


def _load_parser() -> Any:
    spec = importlib.util.spec_from_file_location(
        "bjp_local_hoymiles_dev_parser",
        PARSER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load parser from {PARSER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PARSER = _load_parser()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read and display Hoymiles DTU data without running Home Assistant."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--host", help="DTU IP address or hostname")
    source.add_argument(
        "--fixture",
        type=Path,
        help="Read a saved get-real-data-new JSON payload",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Watch interval in seconds (minimum 35)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Refresh continuously until Ctrl+C",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the normalized snapshot as JSON",
    )
    return parser.parse_args()


async def _fetch_live_payload(
    host: str,
    port: int,
    timeout: int,
) -> dict[str, Any]:
    try:
        from google.protobuf.json_format import MessageToDict
        from hoymiles_wifi.dtu import DTU
    except ModuleNotFoundError as err:
        raise RuntimeError(
            "Live mode requires hoymiles-wifi. Install it with: "
            "python3 -m pip install hoymiles-wifi==0.5.6"
        ) from err

    class PortAwareReadOnlyDTU(DTU):
        async def async_send_request(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            kwargs["dtu_port"] = port
            return await super().async_send_request(*args, **kwargs)

    dtu = PortAwareReadOnlyDTU(host=host, timeout=timeout)
    response = await dtu.async_get_real_data_new()
    if response is None:
        raise RuntimeError(f"No response from {host}:{port}")
    return MessageToDict(
        response,
        preserving_proto_field_name=False,
        always_print_fields_with_no_presence=True,
    )


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _display(value: Any, unit: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        text = f"{value:,.3f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text} {unit}".rstrip()


def _print_row(label: str, value: Any, unit: str = "") -> None:
    print(f"{label:<30} {_display(value, unit):>18}")


def _print_snapshot(snapshot: Any) -> None:
    print("=" * 50)
    print(f"DTU {snapshot.dtu_serial}")
    print("=" * 50)
    _print_row("Timestamp", snapshot.timestamp)
    _print_row("Solar power", snapshot.dtu_power_w, "W")
    _print_row("Home load", snapshot.home_load_power_w, "W")
    _print_row("Daily solar energy", snapshot.dtu_daily_energy_kwh, "kWh")
    _print_row(
        "Lifetime solar energy",
        snapshot.lifetime_solar_energy_kwh,
        "kWh",
    )

    for index, meter in enumerate(snapshot.meters, start=1):
        print(f"\nMeter {index} ({meter.serial})")
        print("-" * 50)
        _print_row("Grid import", meter.grid_import_power_w, "W")
        _print_row("Grid export", meter.grid_export_power_w, "W")
        _print_row("Net grid", meter.net_grid_power_w, "W")
        _print_row("Voltage", meter.voltage_v, "V")
        _print_row("Current", meter.current_a, "A")
        _print_row("Power factor", meter.power_factor)
        _print_row(
            "Imported energy",
            meter.lifetime_imported_energy_kwh,
            "kWh",
        )
        _print_row(
            "Exported energy",
            meter.lifetime_exported_energy_kwh,
            "kWh",
        )

    for inverter in snapshot.inverters:
        print(f"\nInverter {inverter.serial}")
        print("-" * 50)
        _print_row("Status", _link_status(inverter.link_status))
        _print_row("AC power", inverter.active_power_w, "W")
        _print_row("Daily energy", inverter.daily_energy_kwh, "kWh")
        _print_row("Lifetime energy", inverter.lifetime_energy_kwh, "kWh")
        _print_row("AC voltage", inverter.voltage_v, "V")
        _print_row("AC current", inverter.current_a, "A")
        _print_row("Frequency", inverter.frequency_hz, "Hz")
        _print_row("Temperature", inverter.temperature_c, "°C")
        _print_row("Signal", inverter.signal_dbm, "dBm")

        for mppt in snapshot.mppts:
            if mppt.inverter_serial != inverter.serial:
                continue
            prefix = f"MPPT {mppt.port_number}"
            _print_row(f"{prefix} power", mppt.power_w, "W")
            _print_row(f"{prefix} voltage", mppt.voltage_v, "V")
            _print_row(f"{prefix} current", mppt.current_a, "A")


def _link_status(value: int | None) -> str:
    if value == 1:
        return "online"
    if value == 0:
        return "offline"
    return "unknown"


async def _read_once(args: argparse.Namespace) -> Any:
    if args.fixture:
        payload = _load_fixture(args.fixture)
    else:
        payload = await _fetch_live_payload(
            host=args.host,
            port=args.port,
            timeout=args.timeout,
        )
    return PARSER.parse_snapshot(payload)


async def _run(args: argparse.Namespace) -> None:
    if args.watch and args.fixture:
        raise ValueError("--watch is only available with --host")
    if args.watch and args.interval < DEFAULT_INTERVAL:
        raise ValueError("--interval must be at least 35 seconds")

    while True:
        snapshot = await _read_once(args)
        if args.json:
            print(json.dumps(_json_value(snapshot), indent=2, ensure_ascii=False))
        else:
            _print_snapshot(snapshot)

        if not args.watch:
            return
        await asyncio.sleep(args.interval)


def main() -> int:
    args = _arguments()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
