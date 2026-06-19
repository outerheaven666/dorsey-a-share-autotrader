from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.adapters.mapping import MappingPreviewRow


def write_adapter_mapped_preview(rows: list[MappingPreviewRow], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "adapter_mapped_preview.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["provider", "dataset", "source_field", "target_field", "status", "message"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    return path

