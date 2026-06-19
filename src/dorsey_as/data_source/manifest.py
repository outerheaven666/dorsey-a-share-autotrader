from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.data_source.base import DataSource


def write_data_source_manifest(data_source: DataSource, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "data_source_manifest.csv"
    description = data_source.describe()
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dataset", "path", "exists", "mode", "provider", "allow_network"])
        writer.writeheader()
        for dataset, file_path in data_source.files().items():
            writer.writerow(
                {
                    "dataset": dataset,
                    "path": str(file_path),
                    "exists": file_path.exists(),
                    "mode": description.get("mode", ""),
                    "provider": description.get("provider", ""),
                    "allow_network": description.get("allow_network", ""),
                }
            )
    return path
