from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "bjp_local_hoymiles"

FORBIDDEN_PLATFORM_FILES = {
    "button.py",
    "number.py",
    "select.py",
    "switch.py",
}

FORBIDDEN_DTU_METHODS = {
    "async_set_power_limit",
    "async_set_wifi",
    "async_restart_dtu",
    "async_update_dtu_firmware",
    "async_turn_on_inverter",
    "async_turn_off_inverter",
    "async_reboot_inverter",
    "async_enable_performance_data_mode",
    "async_set_energy_storage_working_mode",
}


def test_adapter_public_api_is_read_only() -> None:
    tree = ast.parse((INTEGRATION_DIR / "client.py").read_text())
    public_methods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ReadOnlyHoymilesClient":
            public_methods = {
                item.name
                for item in node.body
                if isinstance(item, ast.AsyncFunctionDef)
                and item.name.startswith("async_")
            }
            break

    assert public_methods == {
        "async_get_app_information",
        "async_get_network_info",
        "async_get_snapshot",
    }


def test_no_control_platform_files_exist() -> None:
    existing = {path.name for path in INTEGRATION_DIR.iterdir()}
    assert existing.isdisjoint(FORBIDDEN_PLATFORM_FILES)


def test_integration_does_not_call_write_methods() -> None:
    for path in INTEGRATION_DIR.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in FORBIDDEN_DTU_METHODS, (
                    f"{path.name} references forbidden DTU method {node.attr}"
                )
