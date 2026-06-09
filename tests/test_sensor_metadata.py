from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components" / "bjp_local_hoymiles" / "sensor.py"
STRINGS = ROOT / "custom_components" / "bjp_local_hoymiles" / "strings.json"
EN_TRANSLATIONS = (
    ROOT / "custom_components" / "bjp_local_hoymiles" / "translations" / "en.json"
)
TH_TRANSLATIONS = (
    ROOT / "custom_components" / "bjp_local_hoymiles" / "translations" / "th.json"
)


def _string_from_expr(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        return "".join(parts)
    raise AssertionError(f"Unsupported string expression: {ast.dump(node)}")


def _state_class_from_call(node: ast.Call) -> str:
    if len(node.args) < 5:
        return "TOTAL_INCREASING"
    arg = node.args[4]
    if isinstance(arg, ast.Attribute):
        return arg.attr
    raise AssertionError(f"Unsupported state class expression: {ast.dump(arg)}")


def _energy_call_map() -> dict[str, str]:
    tree = ast.parse(SENSOR.read_text())
    result: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_energy_description":
            continue
        key = _string_from_expr(node.args[0])
        result[key] = _state_class_from_call(node)
    return result


def test_lifetime_energy_sensors_use_total_state_class() -> None:
    energy_calls = _energy_call_map()

    assert energy_calls["lifetime_solar_energy"] == "TOTAL"
    assert energy_calls["solar_self_consumed_energy"] == "TOTAL"
    assert energy_calls["home_consumption_energy"] == "TOTAL"
    assert any(
        key.endswith("lifetime_imported_energy") and state == "TOTAL"
        for key, state in energy_calls.items()
    )
    assert any(
        key.endswith("lifetime_exported_energy") and state == "TOTAL"
        for key, state in energy_calls.items()
    )
    assert any(
        key.endswith("lifetime_energy") and state == "TOTAL"
        for key, state in energy_calls.items()
    )


def test_daily_energy_sensors_remain_total_increasing() -> None:
    energy_calls = _energy_call_map()

    assert energy_calls["daily_solar_energy"] == "TOTAL_INCREASING"
    assert any(
        key.endswith("daily_energy") and state == "TOTAL_INCREASING"
        for key, state in energy_calls.items()
    )


def test_energy_labels_are_translated() -> None:
    strings = json.loads(STRINGS.read_text())
    en = json.loads(EN_TRANSLATIONS.read_text())
    th = json.loads(TH_TRANSLATIONS.read_text())

    for key in ("solar_self_consumed_energy", "home_consumption_energy"):
        assert key in strings["entity"]["sensor"]
        assert key in en["entity"]["sensor"]
        assert key in th["entity"]["sensor"]
