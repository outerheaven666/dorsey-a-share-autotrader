from __future__ import annotations

import re
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.system_health.models import SensitiveScanFinding, SensitiveScanResult


TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".toml", ".csv", ".txt", ".json"}


def _iter_files(root: Path, scan_path: str) -> list[Path]:
    path = root / scan_path
    if not path.exists():
        return []
    if path.is_file():
        return [path]
    return [item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES]


def _looks_like_pattern_definition(path: Path, line: str, pattern: str) -> bool:
    stripped = line.strip().strip('"').strip("'")
    listed = stripped.startswith("- ") and stripped[2:].strip().strip('"').strip("'") == pattern
    return path.name == "default.yaml" and listed


def _credential_assignment(line: str, pattern: str) -> bool:
    lower = line.lower()
    probe = pattern.lower()
    if probe.endswith("="):
        index = lower.find(probe)
        if index < 0:
            return False
        after = lower[index + len(probe):].strip()
        if after.startswith(('",', "',", "#", ",", "[", "]", ")")):
            return False
        return bool(after)
    if probe not in lower:
        return False
    return bool(re.search(rf"\b{re.escape(probe)}\b\s*[:=]\s*\S+", lower))


def _provider_keyword_finding(path: Path, line: str, keyword: str, allow_docs: bool) -> tuple[str, bool] | None:
    lower = line.lower()
    key = keyword.lower()
    if key not in lower:
        return None
    if path.suffix == ".py" and re.search(rf"\b(import|from)\s+{re.escape(key)}\b", lower):
        return "error", True
    if allow_docs and path.suffix in {".md", ".yaml", ".yml", ".py"}:
        return "warning", False
    return "error", True


def scan_sensitive_content(config: AppConfig, root: Path | None = None) -> SensitiveScanResult:
    if not config.sensitive_scan.enabled:
        return SensitiveScanResult([])
    project_root = root or Path.cwd()
    findings: list[SensitiveScanFinding] = []
    for scan_path in config.sensitive_scan.scan_paths:
        for path in _iter_files(project_root, scan_path):
            try:
                lines = path.read_text(encoding="utf-8-sig").splitlines()
            except UnicodeDecodeError:
                continue
            relative = str(path.relative_to(project_root)) if path.is_relative_to(project_root) else str(path)
            for index, line in enumerate(lines, start=1):
                for pattern in config.sensitive_scan.forbidden_patterns:
                    if _looks_like_pattern_definition(path, line, pattern):
                        continue
                    if _credential_assignment(line, pattern):
                        findings.append(
                            SensitiveScanFinding(
                                path=relative,
                                line=index,
                                pattern=pattern,
                                severity="error",
                                blocking=True,
                                context=line.strip()[:180],
                            )
                        )
                for keyword in config.sensitive_scan.forbidden_provider_keywords:
                    verdict = _provider_keyword_finding(path, line, keyword, config.sensitive_scan.allow_documentation_mentions)
                    if verdict is None:
                        continue
                    severity, blocking = verdict
                    findings.append(
                        SensitiveScanFinding(
                            path=relative,
                            line=index,
                            pattern=keyword,
                            severity=severity,
                            blocking=blocking,
                            context=line.strip()[:180],
                        )
                    )
    return SensitiveScanResult(findings)
