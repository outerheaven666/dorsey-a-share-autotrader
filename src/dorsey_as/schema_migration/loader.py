from __future__ import annotations

from pathlib import Path
from typing import Any

from dorsey_as.schema_migration.models import (
    DeprecatedField,
    FieldAlias,
    FieldMigration,
    MigrationChange,
    MigrationPlan,
)


LIST_SECTIONS = {"field_migrations", "deprecated_fields", "aliases", "breaking_changes", "additive_changes"}
STRING_LISTS = {"required_actions", "rollback_notes", "safety_notes"}


def _parse_scalar(value: str) -> Any:
    raw = value.strip()
    if raw == "[]":
        return []
    if raw in {'""', "''"}:
        return ""
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        return raw.strip('"').strip("'")


def _parse_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_section: str | None = None
    current_item: dict[str, Any] | None = None
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            current_item = None
            key, raw_value = stripped.split(":", 1)
            current_section = key
            if raw_value.strip() == "":
                data[key] = []
            else:
                data[key] = _parse_scalar(raw_value)
            continue

        if current_section in LIST_SECTIONS and indent == 2 and stripped.startswith("- "):
            current_item = {}
            data.setdefault(current_section, []).append(current_item)
            rest = stripped[2:]
            if rest:
                key, raw_value = rest.split(":", 1)
                current_item[key] = _parse_scalar(raw_value)
            continue

        if current_section in STRING_LISTS and indent == 2 and stripped.startswith("- "):
            data.setdefault(current_section, []).append(_parse_scalar(stripped[2:]))
            continue

        if current_item is not None and indent == 4:
            key, raw_value = stripped.split(":", 1)
            current_item[key] = _parse_scalar(raw_value)
    return data


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def load_migration_plan(path: Path | str) -> MigrationPlan:
    plan_path = Path(path)
    raw = _parse_yaml(plan_path)
    field_migrations = [
        FieldMigration(
            dataset=str(item.get("dataset", "")),
            old_field=str(item.get("old_field", "")),
            new_field=str(item.get("new_field", "")),
            change_type=str(item.get("change_type", "")),
            status=str(item.get("status", "")),
            effective_date=str(item.get("effective_date", "")),
            deprecation_date=str(item.get("deprecation_date", "")),
            removal_date=str(item.get("removal_date", "")),
            backward_compatible=_bool(item.get("backward_compatible", False)),
            migration_rule=str(item.get("migration_rule", "")),
            reason=str(item.get("reason", "")),
        )
        for item in raw.get("field_migrations", [])
    ]
    deprecated_fields = [
        DeprecatedField(
            dataset=str(item.get("dataset", "")),
            field=str(item.get("field", "")),
            replacement=str(item.get("replacement", "")),
            status=str(item.get("status", "")),
            deprecation_date=str(item.get("deprecation_date", "")),
            removal_date=str(item.get("removal_date", "")),
            reason=str(item.get("reason", "")),
        )
        for item in raw.get("deprecated_fields", [])
    ]
    aliases = [
        FieldAlias(
            dataset=str(item.get("dataset", "")),
            alias_field=str(item.get("alias_field", "")),
            canonical_field=str(item.get("canonical_field", "")),
            backward_compatible=_bool(item.get("backward_compatible", False)),
            valid_until=str(item.get("valid_until", "")),
        )
        for item in raw.get("aliases", [])
    ]
    breaking_changes = [
        MigrationChange(str(item.get("dataset", "")), str(item.get("field", "")), str(item.get("change_type", "")), str(item.get("reason", "")))
        for item in raw.get("breaking_changes", [])
    ]
    additive_changes = [
        MigrationChange(str(item.get("dataset", "")), str(item.get("field", "")), str(item.get("change_type", "")), str(item.get("reason", "")))
        for item in raw.get("additive_changes", [])
    ]
    return MigrationPlan(
        from_version=str(raw.get("from_version", "")),
        to_version=str(raw.get("to_version", "")),
        effective_date=str(raw.get("effective_date", "")),
        compatibility_window_days=int(raw.get("compatibility_window_days", 0) or 0),
        migration_summary=str(raw.get("migration_summary", "")),
        field_migrations=field_migrations,
        deprecated_fields=deprecated_fields,
        aliases=aliases,
        breaking_changes=breaking_changes,
        additive_changes=additive_changes,
        required_actions=[str(item) for item in raw.get("required_actions", [])],
        rollback_notes=[str(item) for item in raw.get("rollback_notes", [])],
        safety_notes=[str(item) for item in raw.get("safety_notes", [])],
        path=str(plan_path),
    )

