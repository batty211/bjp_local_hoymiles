from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "bjp_local_hoymiles"
BILLING_WIZARD_PATH = PACKAGE_ROOT / "billing_wizard.py"
CONFIG_FLOW_PATH = PACKAGE_ROOT / "config_flow.py"
CONST_PATH = PACKAGE_ROOT / "const.py"


def _ensure_package(name: str) -> types.ModuleType:
    package = sys.modules.get(name)
    if package is not None:
        return package
    package = types.ModuleType(name)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    sys.modules[name] = package
    return package


def load_billing_wizard():
    _ensure_package("custom_components")
    _ensure_package("custom_components.bjp_local_hoymiles")
    const_spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.const",
        CONST_PATH,
    )
    assert const_spec is not None
    assert const_spec.loader is not None
    const_module = importlib.util.module_from_spec(const_spec)
    sys.modules[const_spec.name] = const_module
    const_spec.loader.exec_module(const_module)

    spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.billing_wizard",
        BILLING_WIZARD_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, const_module


def load_config_flow():
    _install_homeassistant_stubs()
    billing_wizard, const = load_billing_wizard()

    client_module = types.ModuleType("custom_components.bjp_local_hoymiles.client")

    class CannotConnectError(Exception):
        pass

    class InvalidResponseError(Exception):
        pass

    class ReadOnlyHoymilesClient:
        def __init__(self, host: str, port: int) -> None:
            self.host = host
            self.port = port

        async def async_get_snapshot(self):
            return None

    client_module.CannotConnectError = CannotConnectError
    client_module.InvalidResponseError = InvalidResponseError
    client_module.ReadOnlyHoymilesClient = ReadOnlyHoymilesClient
    sys.modules[client_module.__name__] = client_module

    spec = importlib.util.spec_from_file_location(
        "custom_components.bjp_local_hoymiles.config_flow",
        CONFIG_FLOW_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, billing_wizard, const


def _install_homeassistant_stubs() -> None:
    voluptuous = types.ModuleType("voluptuous")

    class _Marker:
        def __init__(self, key, default=None) -> None:
            self.schema = key
            self.default = default

        def __hash__(self) -> int:
            return hash((self.schema, self.default))

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, _Marker):
                return NotImplemented
            return (self.schema, self.default) == (other.schema, other.default)

    class Schema(dict):
        def __init__(self, value) -> None:
            super().__init__(value)
            self.schema = value

    def Required(key, default=None):
        return _Marker(key, default)

    def All(*validators):
        return validators

    def Coerce(_type):
        return _type

    def Range(**kwargs):
        return kwargs

    def In(values):
        return tuple(values)

    voluptuous.Schema = Schema
    voluptuous.Required = Required
    voluptuous.All = All
    voluptuous.Coerce = Coerce
    voluptuous.Range = Range
    voluptuous.In = In
    sys.modules["voluptuous"] = voluptuous

    homeassistant = sys.modules.setdefault(
        "homeassistant",
        types.ModuleType("homeassistant"),
    )

    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigFlow:
        def __init_subclass__(cls, *, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.DOMAIN = domain

        async def async_set_unique_id(self, unique_id):
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self, updates=None):
            return None

        def _abort_if_unique_id_mismatch(self):
            return None

        def async_show_form(
            self,
            *,
            step_id,
            data_schema,
            errors=None,
            description_placeholders=None,
        ):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
                "description_placeholders": description_placeholders,
            }

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_update_reload_and_abort(self, entry, data_updates):
            return {
                "type": "abort",
                "reason": "reconfigured",
                "data_updates": data_updates,
            }

    class OptionsFlow:
        def async_show_form(
            self,
            *,
            step_id,
            data_schema,
            errors=None,
            description_placeholders=None,
        ):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
                "description_placeholders": description_placeholders,
            }

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

    class ConfigEntry:
        def __init__(
            self,
            data: dict,
            options: dict,
            entry_id: str = "entry-1",
            unique_id: str = "4121TEST0001",
        ) -> None:
            self.data = data
            self.options = options
            self.entry_id = entry_id
            self.unique_id = unique_id

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigEntry = ConfigEntry
    homeassistant.config_entries = config_entries
    sys.modules["homeassistant.config_entries"] = config_entries

    const_module = types.ModuleType("homeassistant.const")
    const_module.CONF_HOST = "host"
    sys.modules["homeassistant.const"] = const_module

    core = types.ModuleType("homeassistant.core")

    def callback(func):
        return func

    core.callback = callback
    sys.modules["homeassistant.core"] = core

    data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow

    helpers = sys.modules.setdefault(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")

    def async_get(hass):
        return hass.entity_registry

    entity_registry.async_get = async_get
    helpers.entity_registry = entity_registry
    sys.modules["homeassistant.helpers.entity_registry"] = entity_registry


class FakeEntityEntry:
    def __init__(
        self,
        entity_id: str,
        unique_id: str,
        config_entry_id: str,
        domain: str = "sensor",
    ) -> None:
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.config_entry_id = config_entry_id
        self.domain = domain


class FakeEntityRegistry:
    def __init__(self, entities: dict[str, FakeEntityEntry] | None = None) -> None:
        self.entities = entities or {}


class FakeUtilityEntry:
    def __init__(
        self,
        title: str,
        options: dict,
        domain: str = "utility_meter",
        data: dict | None = None,
    ) -> None:
        self.title = title
        self.options = options
        self.domain = domain
        self.data = data or {}


class FakeConfigEntriesManager:
    def __init__(self, entries: list[FakeUtilityEntry]) -> None:
        self._entries = entries

    def async_entries(self, domain: str | None = None):
        if domain is None:
            return list(self._entries)
        return [entry for entry in self._entries if entry.domain == domain]

    def async_get_entry(self, entry_id: str):
        return None


class FakeMeter:
    def __init__(self, serial: str) -> None:
        self.serial = serial


class FakeSnapshot:
    def __init__(self, meters: tuple[FakeMeter, ...]) -> None:
        self.meters = meters


class FakeCoordinator:
    def __init__(self, data: FakeSnapshot) -> None:
        self.data = data


class FakeHass:
    def __init__(
        self,
        entity_registry: FakeEntityRegistry,
        config_entries: FakeConfigEntriesManager,
        data: dict,
    ) -> None:
        self.entity_registry = entity_registry
        self.config_entries = config_entries
        self.data = data


def test_build_billing_cron_for_fixed_day() -> None:
    billing_wizard, const = load_billing_wizard()

    cron = billing_wizard.build_billing_cron(
        const.BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
        "15",
        "17:30",
        "",
    )

    assert cron == "30 17 15 * *"


def test_build_billing_cron_for_last_day() -> None:
    billing_wizard, const = load_billing_wizard()

    cron = billing_wizard.build_billing_cron(
        const.BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
        const.BILLING_RESET_DAY_LAST,
        "08:00",
        "",
    )

    assert cron == "0 8 L * *"


def test_validate_advanced_billing_cron() -> None:
    billing_wizard, const = load_billing_wizard()

    cron = billing_wizard.build_billing_cron(
        const.BILLING_CYCLE_MODE_ADVANCED_CRON,
        "",
        "",
        "0 17 L * *",
    )

    assert cron == "0 17 L * *"


def test_invalid_advanced_billing_cron_raises() -> None:
    billing_wizard, const = load_billing_wizard()

    try:
        billing_wizard.build_billing_cron(
            const.BILLING_CYCLE_MODE_ADVANCED_CRON,
            "",
            "",
            "bad cron",
        )
    except billing_wizard.BillingWizardError as err:
        assert str(err) == "invalid_billing_cron"
    else:
        raise AssertionError("Expected invalid_billing_cron")


def test_find_existing_utility_meter_helpers_matches_source() -> None:
    billing_wizard, _ = load_billing_wizard()

    matches = billing_wizard.find_existing_utility_meter_helpers(
        [
            FakeUtilityEntry(
                title="From Grid Billing",
                options={"source": "sensor.import"},
            ),
            FakeUtilityEntry(
                title="To Grid Billing",
                options={"source": "sensor.export"},
            ),
        ],
        "sensor.import",
    )

    assert matches == ("From Grid Billing",)


def test_find_existing_utility_meter_helpers_matches_data_source() -> None:
    billing_wizard, _ = load_billing_wizard()

    matches = billing_wizard.find_existing_utility_meter_helpers(
        [
            FakeUtilityEntry(
                title="From Grid Billing",
                options={},
                data={"source": "sensor.import"},
            ),
        ],
        "sensor.import",
    )

    assert matches == ("From Grid Billing",)


def test_options_flow_can_disable_billing_wizard() -> None:
    asyncio.run(_test_options_flow_can_disable_billing_wizard())


async def _test_options_flow_can_disable_billing_wizard() -> None:
    config_flow, _, const = load_config_flow()
    entry = config_flow.config_entries.ConfigEntry(
        data={const.CONF_SCAN_INTERVAL: 35},
        options={},
    )
    flow = config_flow.BjpLocalHoymilesOptionsFlow(entry)
    flow.hass = FakeHass(FakeEntityRegistry(), FakeConfigEntriesManager([]), {})

    result = await flow.async_step_init(
        {
            const.CONF_SCAN_INTERVAL: 60,
            const.CONF_BILLING_CYCLE_ENABLED: False,
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"][const.CONF_SCAN_INTERVAL] == 60
    assert result["data"][const.CONF_BILLING_CYCLE_ENABLED] is False


def test_options_flow_review_includes_import_and_export_recipes() -> None:
    asyncio.run(_test_options_flow_review_includes_import_and_export_recipes())


async def _test_options_flow_review_includes_import_and_export_recipes() -> None:
    config_flow, _, const = load_config_flow()
    entry = config_flow.config_entries.ConfigEntry(
        data={const.CONF_SCAN_INTERVAL: 35},
        options={},
        entry_id="entry-1",
        unique_id="4121TEST0001",
    )
    flow = config_flow.BjpLocalHoymilesOptionsFlow(entry)
    flow.hass = FakeHass(
        entity_registry=FakeEntityRegistry(
            entities={
                "import": FakeEntityEntry(
                    entity_id="sensor.hoymiles_meter_18417181655590_lifetime_imported_energy",
                    unique_id="4121TEST0001_meter_18417181655590_18417181655590_lifetime_imported_energy",
                    config_entry_id="entry-1",
                ),
                "export": FakeEntityEntry(
                    entity_id="sensor.hoymiles_meter_18417181655590_lifetime_exported_energy",
                    unique_id="4121TEST0001_meter_18417181655590_18417181655590_lifetime_exported_energy",
                    config_entry_id="entry-1",
                ),
            }
        ),
        config_entries=FakeConfigEntriesManager([]),
        data={
            const.DOMAIN: {
                "entry-1": FakeCoordinator(FakeSnapshot((FakeMeter("18417181655590"),)))
            }
        },
    )

    first = await flow.async_step_init(
        {
            const.CONF_SCAN_INTERVAL: 45,
            const.CONF_BILLING_CYCLE_ENABLED: True,
        }
    )
    assert first["step_id"] == "billing"

    review = await flow.async_step_billing(
        {
            const.CONF_BILLING_CYCLE_MODE: const.BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
            const.CONF_BILLING_RESET_DAY: "15",
            const.CONF_BILLING_RESET_TIME: "17:30",
        }
    )

    assert review["step_id"] == "review"
    text = review["description_placeholders"]["review_text"]
    assert "sensor.hoymiles_meter_18417181655590_lifetime_imported_energy" in text
    assert "sensor.hoymiles_meter_18417181655590_lifetime_exported_energy" in text
    assert "cron: 30 17 15 * *" in text
    assert "existing utility_meter helpers: not found" in text


def test_options_flow_review_shows_existing_helper_status() -> None:
    asyncio.run(_test_options_flow_review_shows_existing_helper_status())


async def _test_options_flow_review_shows_existing_helper_status() -> None:
    config_flow, _, const = load_config_flow()
    entry = config_flow.config_entries.ConfigEntry(
        data={const.CONF_SCAN_INTERVAL: 35},
        options={},
        entry_id="entry-1",
        unique_id="4121TEST0001",
    )
    flow = config_flow.BjpLocalHoymilesOptionsFlow(entry)
    import_entity = "sensor.hoymiles_meter_18417181655590_lifetime_imported_energy"
    export_entity = "sensor.hoymiles_meter_18417181655590_lifetime_exported_energy"
    flow.hass = FakeHass(
        entity_registry=FakeEntityRegistry(
            entities={
                "import": FakeEntityEntry(
                    entity_id=import_entity,
                    unique_id="4121TEST0001_meter_18417181655590_18417181655590_lifetime_imported_energy",
                    config_entry_id="entry-1",
                ),
                "export": FakeEntityEntry(
                    entity_id=export_entity,
                    unique_id="4121TEST0001_meter_18417181655590_18417181655590_lifetime_exported_energy",
                    config_entry_id="entry-1",
                ),
            }
        ),
        config_entries=FakeConfigEntriesManager(
            [
                FakeUtilityEntry("Billing Import", {"source": import_entity}),
                FakeUtilityEntry("Billing Export", {"source": export_entity}),
            ]
        ),
        data={
            const.DOMAIN: {
                "entry-1": FakeCoordinator(FakeSnapshot((FakeMeter("18417181655590"),)))
            }
        },
    )

    await flow.async_step_init(
        {
            const.CONF_SCAN_INTERVAL: 45,
            const.CONF_BILLING_CYCLE_ENABLED: True,
        }
    )
    review = await flow.async_step_billing(
        {
            const.CONF_BILLING_CYCLE_MODE: const.BILLING_CYCLE_MODE_ADVANCED_CRON,
            const.CONF_BILLING_CRON: "0 17 L * *",
        }
    )

    text = review["description_placeholders"]["review_text"]
    assert "Billing Import" in text
    assert "Billing Export" in text
    assert "cron: 0 17 L * *" in text
