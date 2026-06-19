from __future__ import annotations

from dorsey_as.schema_versioning.models import ContractDiffReport, ContractDiffRow, DatasetContract, ProviderContract


def _row(dataset: str, field: str, change_type: str, severity: str, baseline: object, candidate: object, breaking: bool, message: str) -> ContractDiffRow:
    return ContractDiffRow(
        dataset=dataset,
        field=field,
        change_type=change_type,
        severity=severity,
        baseline_value=str(baseline),
        candidate_value=str(candidate),
        breaking=breaking,
        message=message,
    )


def _compare_field_sets(dataset: str, baseline: DatasetContract, candidate: DatasetContract) -> list[ContractDiffRow]:
    rows: list[ContractDiffRow] = []
    baseline_required = set(baseline.required_fields)
    candidate_required = set(candidate.required_fields)
    baseline_optional = set(baseline.optional_fields)
    candidate_optional = set(candidate.optional_fields)

    for field in sorted(baseline_required - candidate_required):
        rows.append(_row(dataset, field, "required_field_removed", "error", "required", "missing", True, "Required field was removed from candidate contract."))
    for field in sorted(candidate_optional - baseline_optional - baseline_required):
        rows.append(_row(dataset, field, "additive_optional_field", "warning", "missing", "optional", False, "Documented optional field was added."))
    return rows


def _compare_field_types(dataset: str, baseline: DatasetContract, candidate: DatasetContract) -> list[ContractDiffRow]:
    rows: list[ContractDiffRow] = []
    required_fields = set(baseline.required_fields)
    for field in sorted(set(baseline.field_types) & set(candidate.field_types)):
        base_type = baseline.field_types[field]
        candidate_type = candidate.field_types[field]
        if base_type != candidate_type:
            breaking = field in required_fields
            rows.append(
                _row(
                    dataset,
                    field,
                    "field_type_changed",
                    "error" if breaking else "warning",
                    base_type,
                    candidate_type,
                    breaking,
                    "Required field type changed." if breaking else "Optional field type changed.",
                )
            )
    return rows


def _compare_category(dataset: str, category: str, baseline_fields: list[str], candidate_fields: list[str]) -> list[ContractDiffRow]:
    rows: list[ContractDiffRow] = []
    for field in sorted(set(baseline_fields) - set(candidate_fields)):
        rows.append(_row(dataset, field, f"{category}_field_removed", "error", category, "missing", True, f"{category} field changed to a non-{category} field."))
    return rows


def diff_contracts(baseline: ProviderContract, candidate: ProviderContract, block_on_breaking_change: bool = True) -> ContractDiffReport:
    rows: list[ContractDiffRow] = []
    baseline_datasets = set(baseline.datasets)
    candidate_datasets = set(candidate.datasets)

    for dataset in sorted(baseline_datasets - candidate_datasets):
        rows.append(_row(dataset, "", "dataset_removed", "error", "present", "missing", True, "Dataset was removed from candidate contract."))
    for dataset in sorted(candidate_datasets - baseline_datasets):
        rows.append(_row(dataset, "", "additive_dataset", "warning", "missing", "present", False, "Dataset was added without changing existing datasets."))

    for dataset in sorted(baseline_datasets & candidate_datasets):
        base_dataset = baseline.datasets[dataset]
        candidate_dataset = candidate.datasets[dataset]
        if base_dataset.primary_key != candidate_dataset.primary_key:
            rows.append(_row(dataset, "primary_key", "primary_key_changed", "error", base_dataset.primary_key, candidate_dataset.primary_key, True, "Primary key changed."))
        rows.extend(_compare_field_sets(dataset, base_dataset, candidate_dataset))
        rows.extend(_compare_field_types(dataset, base_dataset, candidate_dataset))
        rows.extend(_compare_category(dataset, "date", base_dataset.date_fields, candidate_dataset.date_fields))
        rows.extend(_compare_category(dataset, "numeric", base_dataset.numeric_fields, candidate_dataset.numeric_fields))
        rows.extend(_compare_category(dataset, "boolean", base_dataset.boolean_fields, candidate_dataset.boolean_fields))

    if not rows:
        rows.append(_row("", "", "compatible_no_change", "info", baseline.version, candidate.version, False, "Contracts are compatible with no detected changes."))
    return ContractDiffReport(baseline.path, candidate.path, rows, block_on_breaking_change)

