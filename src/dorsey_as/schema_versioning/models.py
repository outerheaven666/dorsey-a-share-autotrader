from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetContract:
    name: str
    version: str
    description: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    field_types: dict[str, str] = field(default_factory=dict)
    date_fields: list[str] = field(default_factory=list)
    numeric_fields: list[str] = field(default_factory=list)
    boolean_fields: list[str] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderContract:
    version: str
    description: str
    datasets: dict[str, DatasetContract]
    path: str = ""


@dataclass(frozen=True)
class ContractDiffRow:
    dataset: str
    field: str
    change_type: str
    severity: str
    baseline_value: str
    candidate_value: str
    breaking: bool
    message: str


@dataclass(frozen=True)
class ContractDiffReport:
    baseline_path: str
    candidate_path: str
    rows: list[ContractDiffRow]
    block_on_breaking_change: bool = True

    @property
    def breaking_count(self) -> int:
        return sum(1 for row in self.rows if row.breaking)

    @property
    def additive_count(self) -> int:
        return sum(1 for row in self.rows if row.change_type.startswith("additive"))

    @property
    def compatible_count(self) -> int:
        return sum(1 for row in self.rows if row.change_type.startswith("compatible"))

    @property
    def blocking_decision(self) -> bool:
        return self.block_on_breaking_change and self.breaking_count > 0

