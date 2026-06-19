from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldMigration:
    dataset: str
    old_field: str
    new_field: str
    change_type: str
    status: str
    effective_date: str
    deprecation_date: str
    removal_date: str
    backward_compatible: bool
    migration_rule: str
    reason: str


@dataclass(frozen=True)
class DeprecatedField:
    dataset: str
    field: str
    replacement: str
    status: str
    deprecation_date: str
    removal_date: str
    reason: str


@dataclass(frozen=True)
class FieldAlias:
    dataset: str
    alias_field: str
    canonical_field: str
    backward_compatible: bool
    valid_until: str


@dataclass(frozen=True)
class MigrationChange:
    dataset: str
    field: str
    change_type: str
    reason: str


@dataclass(frozen=True)
class MigrationPlan:
    from_version: str
    to_version: str
    effective_date: str
    compatibility_window_days: int
    migration_summary: str
    field_migrations: list[FieldMigration] = field(default_factory=list)
    deprecated_fields: list[DeprecatedField] = field(default_factory=list)
    aliases: list[FieldAlias] = field(default_factory=list)
    breaking_changes: list[MigrationChange] = field(default_factory=list)
    additive_changes: list[MigrationChange] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    rollback_notes: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    path: str = ""


@dataclass(frozen=True)
class MigrationCheckRow:
    from_version: str
    to_version: str
    dataset: str
    field: str
    check_type: str
    status: str
    severity: str
    message: str


@dataclass(frozen=True)
class MigrationValidationReport:
    plan: MigrationPlan
    rows: list[MigrationCheckRow]

    @property
    def blocking_decision(self) -> bool:
        return any(row.status == "fail" and row.severity == "error" for row in self.rows)

    @property
    def expired_deprecation_count(self) -> int:
        return sum(1 for row in self.rows if row.check_type == "expired_deprecation")

    @property
    def pending_deprecation_count(self) -> int:
        return sum(1 for row in self.rows if row.check_type == "pending_deprecation")

