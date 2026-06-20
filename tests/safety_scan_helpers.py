from __future__ import annotations

import re
from pathlib import Path


PROVIDER_KEYWORDS = ["akshare", "tushare", "wind", "choice", "jqdata", "joinquant", "jqdatasdk", "qmt", "ptrade"]
CREDENTIAL_ASSIGNMENT_RE = re.compile(r"(token|secret|password|webhook_url|credential)=['\"]?[A-Za-z0-9_\-]{3,}")
REAL_IMPORT_RE = re.compile(r"\b(import|from)\s+(akshare|tushare|wind|choice|jqdata|jqdatasdk|qmt|ptrade)\b")
REAL_CLASS_RE = re.compile(r"\b(class|def)\s+(akshare|tushare|wind|choice|jqdata|jqdatasdk|qmt|ptrade)[A-Za-z_]*")
REAL_REGISTRY_RE = re.compile(r"\b(get_provider|register|registry|return)\b.*\b(akshare|tushare|wind|choice|jqdata|jqdatasdk|qmt|ptrade)\b")


def _text_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".yaml", ".yml", ".md", ".csv", ".toml"}:
                files.append(path)
    return files


def is_allowed_provider_mention(path: Path, line: str) -> bool:
    lower = line.lower()
    stripped = line.strip()
    if path.suffix == ".md":
        return True
    if path.name == "default.yaml" and (stripped.startswith("- ") or "forbidden_provider_keywords" in lower):
        return True
    if path.name == "models.py" and "forbidden_provider_keywords" in lower:
        return True
    safety_context = ["disabled", "not connected", "no real", "forbidden", "mock", "contract", "safety", "not enabled"]
    return any(marker in lower for marker in safety_context)


def assert_no_real_provider_or_broker_integration(roots: list[Path]) -> None:
    violations: list[str] = []
    for path in _text_files(roots):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lower = line.lower()
            if CREDENTIAL_ASSIGNMENT_RE.search(lower):
                violations.append(f"{path}:{line_number}: credential-like assignment")
            if REAL_IMPORT_RE.search(lower):
                violations.append(f"{path}:{line_number}: real provider SDK import")
            if REAL_CLASS_RE.search(lower):
                violations.append(f"{path}:{line_number}: real provider/broker class or function")
            if REAL_REGISTRY_RE.search(lower) and not is_allowed_provider_mention(path, line):
                violations.append(f"{path}:{line_number}: real provider/broker registry usage")
            if any(re.search(rf"\b{re.escape(word)}\b", lower) for word in PROVIDER_KEYWORDS):
                if not is_allowed_provider_mention(path, line) and not (REAL_IMPORT_RE.search(lower) or REAL_CLASS_RE.search(lower) or REAL_REGISTRY_RE.search(lower)):
                    violations.append(f"{path}:{line_number}: undocumented provider/broker mention")
    assert not violations, "\n".join(violations)
