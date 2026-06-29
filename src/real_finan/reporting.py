from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def export_run_artifacts(result: dict[str, Any], output_dir: Path, thread_id: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{thread_id}_{timestamp}"

    report_path = output_dir / f"{base_name}_report.md"
    audit_path = output_dir / f"{base_name}_audit.json"
    state_path = output_dir / f"{base_name}_state.json"

    report_path.write_text(result["final_report"], encoding="utf-8")
    audit_path.write_text(
        json.dumps(result.get("audit_log", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    state_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return {
        "report_path": str(report_path),
        "audit_path": str(audit_path),
        "state_path": str(state_path),
    }
