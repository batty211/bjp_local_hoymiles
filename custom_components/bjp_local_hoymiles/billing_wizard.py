"""Utility Meter billing wizard helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time
from typing import Any

from .const import (
    BILLING_CYCLE_MODE_ADVANCED_CRON,
    BILLING_CYCLE_MODE_SIMPLE_MONTHLY,
    BILLING_RESET_DAY_LAST,
)

UTILITY_METER_DOMAIN = "utility_meter"
UTILITY_METER_SOURCE_OPTION = "source"
UTILITY_METER_DELTA_VALUES = "false"
UTILITY_METER_PERIODICALLY_RESETTING = "false"
UTILITY_METER_ALWAYS_AVAILABLE = "true"
_CRON_FIELD_PATTERN = re.compile(r"^[0-9*/,\-]+$")


class BillingWizardError(ValueError):
    """Raised when the billing wizard input is invalid."""


@dataclass(frozen=True, slots=True)
class BillingHelperRecipe:
    """Suggested Utility Meter helper configuration."""

    label: str
    source_entity_id: str
    cron: str
    existing_helpers: tuple[str, ...] = ()


def normalize_billing_time(value: str) -> str:
    """Normalize a billing reset time into HH:MM."""
    try:
        parsed = time.fromisoformat(value.strip())
    except (AttributeError, ValueError) as err:
        raise BillingWizardError("invalid_billing_time") from err
    return parsed.strftime("%H:%M")


def build_billing_cron(
    mode: str,
    reset_day: str,
    reset_time: str,
    advanced_cron: str,
) -> str:
    """Build the Utility Meter cron expression from wizard settings."""
    if mode == BILLING_CYCLE_MODE_SIMPLE_MONTHLY:
        normalized_time = normalize_billing_time(reset_time)
        hour, minute = normalized_time.split(":")
        day_field = _validate_reset_day(reset_day)
        return f"{int(minute)} {int(hour)} {day_field} * *"
    if mode == BILLING_CYCLE_MODE_ADVANCED_CRON:
        return validate_billing_cron(advanced_cron)
    raise BillingWizardError("invalid_billing_mode")


def validate_billing_cron(pattern: str) -> str:
    """Perform a lightweight validation of an advanced cron pattern."""
    normalized = " ".join(pattern.split())
    fields = normalized.split(" ")
    if len(fields) != 5:
        raise BillingWizardError("invalid_billing_cron")

    for index, field in enumerate(fields):
        if index == 2 and field == "L":
            continue
        if not _CRON_FIELD_PATTERN.fullmatch(field):
            raise BillingWizardError("invalid_billing_cron")
    return normalized


def find_existing_utility_meter_helpers(
    entries: list[Any],
    source_entity_id: str,
) -> tuple[str, ...]:
    """Return matching Utility Meter helper titles for a source entity."""
    matches: list[str] = []
    for entry in entries:
        if getattr(entry, "domain", None) != UTILITY_METER_DOMAIN:
            continue
        options = getattr(entry, "options", {})
        data = getattr(entry, "data", {})
        source = options.get(UTILITY_METER_SOURCE_OPTION) or data.get(
            UTILITY_METER_SOURCE_OPTION
        )
        if source == source_entity_id:
            matches.append(getattr(entry, "title", source_entity_id))
    return tuple(matches)


def build_review_text(
    import_recipe: BillingHelperRecipe,
    export_recipe: BillingHelperRecipe,
) -> str:
    """Build the review text shown in the options flow."""
    parts = [
        "Save these options, then create two Utility Meter helpers manually.",
        (
            "This integration does not create or edit helpers during "
            "HACS install/update or runtime."
        ),
        _format_recipe(import_recipe),
        _format_recipe(export_recipe),
        "Set these exact Utility Meter fields for both helpers:",
        "delta_values: false\nperiodically_resetting: false\nalways_available: true",
    ]
    return "\n\n".join(parts)


def _format_recipe(recipe: BillingHelperRecipe) -> str:
    helper_names = (
        ", ".join(recipe.existing_helpers)
        if recipe.existing_helpers
        else "not found"
    )
    return (
        f"{recipe.label}\n"
        f"source: {recipe.source_entity_id}\n"
        f"cron: {recipe.cron}\n"
        f"existing utility_meter helpers: {helper_names}"
    )


def _validate_reset_day(value: str) -> str:
    if value == BILLING_RESET_DAY_LAST:
        return "L"
    try:
        day = int(value)
    except (TypeError, ValueError) as err:
        raise BillingWizardError("invalid_billing_reset_day") from err
    if day < 1 or day > 28:
        raise BillingWizardError("invalid_billing_reset_day")
    return str(day)
