from __future__ import annotations

from pathlib import Path
from typing import Any

from dorsey_as.schema_versioning.models import DatasetContract, ProviderContract


LIST_FIELDS = {"required_fields", "optional_fields", "date_fields", "numeric_fields", "boolean_fields", "primary_key"}
DICT_FIELDS = {"field_types"}


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
    return raw.strip('"').strip("'")


def _parse_contract_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {"datasets": {}}
    current_dataset: str | None = None
    current_field: str | None = None
    in_datasets = False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            current_dataset = None
            current_field = None
            if stripped == "datasets:":
                in_datasets = True
                continue
            key, raw_value = stripped.split(":", 1)
            data[key] = _parse_scalar(raw_value)
            continue

        if in_datasets and indent == 2 and stripped.endswith(":"):
            current_dataset = stripped[:-1]
            data["datasets"][current_dataset] = {}
            current_field = None
            continue

        if current_dataset is None:
            continue

        dataset_data = data["datasets"][current_dataset]
        if indent == 4:
            key, raw_value = stripped.split(":", 1)
            current_field = key
            if raw_value.strip() == "":
                dataset_data[key] = {} if key in DICT_FIELDS else []
            else:
                dataset_data[key] = _parse_scalar(raw_value)
            continue

        if indent == 6 and stripped.startswith("- ") and current_field:
            values = dataset_data.setdefault(current_field, [])
            values.append(_parse_scalar(stripped[2:]))
            continue

        if indent == 6 and current_field in DICT_FIELDS:
            key, raw_value = stripped.split(":", 1)
            dataset_data.setdefault(current_field, {})[key.strip()] = str(_parse_scalar(raw_value))
            continue
    return data


def load_provider_contract(path: Path | str) -> ProviderContract:
    contract_path = Path(path)
    raw = _parse_contract_yaml(contract_path)
    datasets: dict[str, DatasetContract] = {}
    for name, dataset in raw.get("datasets", {}).items():
        datasets[name] = DatasetContract(
            name=name,
            version=str(dataset.get("version", "")),
            description=str(dataset.get("description", "")),
            required_fields=list(dataset.get("required_fields", [])),
            optional_fields=list(dataset.get("optional_fields", [])),
            field_types=dict(dataset.get("field_types", {})),
            date_fields=list(dataset.get("date_fields", [])),
            numeric_fields=list(dataset.get("numeric_fields", [])),
            boolean_fields=list(dataset.get("boolean_fields", [])),
            primary_key=list(dataset.get("primary_key", [])),
        )
    return ProviderContract(
        version=str(raw.get("version", "")),
        description=str(raw.get("description", "")),
        datasets=datasets,
        path=str(contract_path),
    )

