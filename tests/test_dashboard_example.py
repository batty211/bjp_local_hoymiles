from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "docs" / "examples" / "power-monitor-2026.yaml"

EXPECTED_ENTITIES = {
    "sensor.bjp_local_hoymiles_dtu_solar_power",
    "sensor.bjp_local_hoymiles_dtu_home_load_power",
    "sensor.bjp_local_hoymiles_dtu_connection_status",
    "sensor.bjp_local_hoymiles_dtu_daily_solar_energy",
    "sensor.bjp_local_hoymiles_dtu_lifetime_solar_energy",
    "sensor.bjp_local_hoymiles_dtu_solar_self_consumed_energy",
    "sensor.bjp_local_hoymiles_dtu_home_consumption_energy",
    "sensor.bjp_local_hoymiles_dtu_last_update",
    "sensor.hoymiles_meter_18417181655590_grid_import_power",
    "sensor.hoymiles_meter_18417181655590_grid_export_power",
    "sensor.hoymiles_meter_18417181655590_net_grid_power",
    "sensor.hoymiles_meter_18417181655590_lifetime_imported_energy",
    "sensor.hoymiles_meter_18417181655590_lifetime_exported_energy",
    "sensor.hoymiles_meter_18417181655590_voltage",
    "sensor.hoymiles_meter_18417181655590_current",
    "sensor.hoymiles_meter_18417181655590_power_factor",
}


def test_dashboard_example_uses_energy_date_selection_and_custom_graph() -> None:
    dashboard = DASHBOARD.read_text()

    assert "type: energy-date-selection" in dashboard
    assert "type: statistics-graph" in dashboard
    assert "type: tile" in dashboard
    assert "type: statistic" in dashboard
    assert "type: sections" in dashboard


def test_dashboard_example_references_expected_entities() -> None:
    dashboard = DASHBOARD.read_text()
    entities = {
        match.group(1)
        for match in re.finditer(r"entity:\s*(sensor\.[A-Za-z0-9_]+)", dashboard)
    }

    assert EXPECTED_ENTITIES <= entities
    assert len(entities) == len(EXPECTED_ENTITIES)


def test_dashboard_example_uses_app_like_layout_sections() -> None:
    dashboard = DASHBOARD.read_text()

    assert "heading: ภาพรวมขณะนี้" in dashboard
    assert "heading: ช่วงวันที่เลือก" in dashboard
    assert "heading: Meter" in dashboard
    assert "heading: กราฟตามช่วงวันที่เลือก" in dashboard
    assert "title: ผลิต / โหลด / กริด" in dashboard
    assert "title: Import / Export Grid" in dashboard
