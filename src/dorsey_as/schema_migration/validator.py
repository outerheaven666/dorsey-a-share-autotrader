from __future__ import annotations

from datetime import date

from dorsey_as.config.models import SchemaMigrationConfig
from dorsey_as.schema_migration.models import MigrationCheckRow, MigrationPlan, MigrationValidationReport


def _as_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _row(plan: MigrationPlan, dataset: str, field: str, check_type: str, status: str, severity: str, message: str) -> MigrationCheckRow:
    return MigrationCheckRow(plan.from_version, plan.to_version, dataset, field, check_type, status, severity, message)


def validate_migration_plan(plan: MigrationPlan, config: SchemaMigrationConfig, as_of_date: str = "2026-06-19") -> MigrationValidationReport:
    rows: list[MigrationCheckRow] = []
    current_date = _as_date(as_of_date) or date.today()
    rows.append(
        _row(
            plan,
            "",
            "",
            "version_pair",
            "pass" if plan.from_version == config.current_version and plan.to_version == config.target_version else "fail",
            "info" if plan.from_version == config.current_version and plan.to_version == config.target_version else "error",
            f"{plan.from_version}->{plan.to_version}",
        )
    )
    rows.append(
        _row(
            plan,
            "",
            "",
            "compatibility_window",
            "pass" if plan.compatibility_window_days == config.compatibility_window_days else "warn",
            "info" if plan.compatibility_window_days == config.compatibility_window_days else "warning",
            f"window_days={plan.compatibility_window_days}",
        )
    )

    for migration in plan.field_migrations:
        if migration.change_type != "no_change" and not migration.migration_rule.strip():
            rows.append(_row(plan, migration.dataset, migration.new_field or migration.old_field, "missing_migration_rule", "fail", "error", "migration_rule is required"))
        else:
            rows.append(_row(plan, migration.dataset, migration.new_field or migration.old_field, "migration_rule", "pass", "info", migration.migration_rule or "no change"))

        removal = _as_date(migration.removal_date)
        deprecation = _as_date(migration.deprecation_date)
        if removal and current_date > removal and migration.status in {"deprecated", "pending_removal"}:
            rows.append(_row(plan, migration.dataset, migration.old_field, "expired_deprecation", "fail", "error", f"removal_date={migration.removal_date} has passed"))
        elif deprecation and current_date >= deprecation and migration.status in {"deprecated", "pending_removal"}:
            rows.append(_row(plan, migration.dataset, migration.old_field, "pending_deprecation", "warn", "warning", f"deprecation_date={migration.deprecation_date} is active"))

    for deprecated in plan.deprecated_fields:
        removal = _as_date(deprecated.removal_date)
        deprecation = _as_date(deprecated.deprecation_date)
        if removal and current_date > removal:
            rows.append(_row(plan, deprecated.dataset, deprecated.field, "expired_deprecation", "fail", "error", f"deprecated field removal_date={deprecated.removal_date} has passed"))
        elif deprecation and current_date >= deprecation:
            rows.append(_row(plan, deprecated.dataset, deprecated.field, "pending_deprecation", "warn", "warning", f"deprecated field active until {deprecated.removal_date}"))

    for alias in plan.aliases:
        status = "pass" if alias.backward_compatible and config.allow_backward_compatible_aliases else "fail"
        severity = "info" if status == "pass" else "error"
        rows.append(_row(plan, alias.dataset, alias.alias_field, "backward_compatible_alias", status, severity, f"canonical={alias.canonical_field}, valid_until={alias.valid_until}"))

    if plan.breaking_changes and not plan.required_actions:
        for change in plan.breaking_changes:
            rows.append(_row(plan, change.dataset, change.field, "breaking_without_action", "fail", "error", "breaking change requires at least one required_action"))
    elif plan.breaking_changes:
        for change in plan.breaking_changes:
            rows.append(_row(plan, change.dataset, change.field, "breaking_change_action", "pass", "info", "breaking change has required action metadata"))

    if len(rows) == 2:
        rows.append(_row(plan, "", "", "migration_metadata", "pass", "info", "migration metadata loaded"))
    return MigrationValidationReport(plan, rows)


def build_compatibility_matrix(plan: MigrationPlan, as_of_date: str = "2026-06-19") -> list[dict[str, str]]:
    current_date = _as_date(as_of_date) or date.today()
    rows: list[dict[str, str]] = []
    for migration in plan.field_migrations:
        removal = _as_date(migration.removal_date)
        if removal and current_date > removal:
            lifecycle = "expired"
        elif migration.status in {"deprecated", "pending_removal"}:
            lifecycle = migration.status
        else:
            lifecycle = "active"
        rows.append(
            {
                "dataset": migration.dataset,
                "field": migration.old_field or migration.new_field,
                "canonical_field": migration.new_field,
                "status": lifecycle,
                "backward_compatible": str(migration.backward_compatible),
                "valid_until": migration.removal_date,
            }
        )
    for alias in plan.aliases:
        rows.append(
            {
                "dataset": alias.dataset,
                "field": alias.alias_field,
                "canonical_field": alias.canonical_field,
                "status": "alias",
                "backward_compatible": str(alias.backward_compatible),
                "valid_until": alias.valid_until,
            }
        )
    return rows

