from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dorsey_as.config.models import NotifyConfig


def send_feishu_notification(payload: dict[str, Any], config: NotifyConfig, output_dir: Path) -> dict[str, Any]:
    if not config.enabled or config.mode == "dry_run":
        return {"sent": False, "reason": "dry_run_or_disabled"}

    webhook = os.environ.get(config.webhook_url_env)
    if not webhook:
        raise RuntimeError(f"{config.webhook_url_env} is required when notify.enabled=true and notify.mode=send")

    # MVP 5 intentionally does not perform network I/O. This keeps notifications auditable and safe by default.
    return {"sent": False, "reason": "real_network_send_not_implemented_in_mvp", "env_var": config.webhook_url_env}
