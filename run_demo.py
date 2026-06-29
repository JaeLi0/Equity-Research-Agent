from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.real_finan import FinanceMultiAgentSystem
from src.real_finan.config import AppConfig
from src.real_finan.reporting import export_run_artifacts


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run the enterprise real_finan demo.")
    parser.add_argument(
        "--query",
        default="对比分析 Apple 与 Microsoft 2025 年最新财报的供应链风险与研发投入，并生成合规审计报告。",
        help="User query for the multi-agent system.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full final state as JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to store generated markdown and JSON artifacts.",
    )
    parser.add_argument(
        "--thread-id",
        default="demo-thread",
        help="Thread identifier used by the LangGraph checkpointer.",
    )
    args = parser.parse_args()

    config = AppConfig.from_env()
    output_dir = Path(args.output_dir) if args.output_dir else config.output_dir

    app = FinanceMultiAgentSystem()
    result = app.run(args.query, thread_id=args.thread_id)
    artifacts = export_run_artifacts(result, output_dir=output_dir, thread_id=args.thread_id)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["final_report"])
        print(f"\n[LLM] backend={result.get('llm_backend', 'unknown')}")
        print(f"\n[Artifacts] report={artifacts['report_path']}")
        print(f"[Artifacts] audit={artifacts['audit_path']}")
        print(f"[Artifacts] state={artifacts['state_path']}")


if __name__ == "__main__":
    main()
