from __future__ import annotations

from dorsey_as.safety.models import SafetyChecklist, SafetyGateResult


def build_safety_checklist(result: SafetyGateResult) -> SafetyChecklist:
    return SafetyChecklist(items=result.rows)

