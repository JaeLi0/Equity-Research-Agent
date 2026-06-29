from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from uuid import uuid4
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from real_finan import FinanceMultiAgentSystem
from real_finan.api.app import create_app
from real_finan.config import AppConfig
from real_finan.llm import LLMSettings
from real_finan.reporting import export_run_artifacts


def build_test_config(root: Path, api_key: str | None = None) -> AppConfig:
    db_path = root / "data" / "real_finan.db"
    return AppConfig(
        output_dir=root / "outputs",
        upload_dir=root / "uploads",
        db_path=db_path,
        database_url=f"sqlite:///{db_path.as_posix()}",
        redis_url=None,
        redis_queue_name="finance-analysis-test",
        neo4j_uri=None,
        neo4j_username=None,
        neo4j_password=None,
        market_data_provider="yahoo",
        alphavantage_api_key=None,
        host="127.0.0.1",
        port=8000,
        api_key=api_key,
        llm=LLMSettings(api_key=None, base_url="https://api.deepseek.com", model="deepseek-chat", timeout_seconds=45),
    )


class FinanceSystemTestCase(unittest.TestCase):
    def test_end_to_end_report_generation(self) -> None:
        app = FinanceMultiAgentSystem()
        result = app.run("对比分析 Apple 与 Microsoft 的供应链风险和研发投入。", thread_id="test-e2e")

        self.assertIn("final_report", result)
        self.assertIn("Apple", result["final_report"])
        self.assertIn("Microsoft", result["final_report"])
        self.assertGreaterEqual(result["checkpoint_count"], 1)
        self.assertIn(result["llm_backend"], {"deepseek", "local-fallback"})

    def test_replanner_path_and_exports(self) -> None:
        app = FinanceMultiAgentSystem()
        result = app.run("分析 Apple 2025 财报的供应链附录风险。", thread_id="test-replanner")

        steps = [event["step"] for event in result["audit_log"]]
        self.assertIn("retrieval", steps)
        self.assertIn("quant", steps)

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifacts = export_run_artifacts(result, Path(tmp_dir), "test-replanner")
            for artifact_path in artifacts.values():
                self.assertTrue(Path(artifact_path).exists())

            state_payload = json.loads(Path(artifacts["state_path"]).read_text(encoding="utf-8"))
            self.assertEqual(state_payload["thread_id"], "test-replanner")

    def test_api_endpoint(self) -> None:
        tmp_root = ROOT / "test_artifacts" / f"api-test-{uuid4().hex[:8]}"
        tmp_root.mkdir(parents=True, exist_ok=True)
        app = create_app(build_test_config(tmp_root, api_key=None))
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                json={
                    "query": "对比分析 Apple 与 Microsoft 的供应链风险和研发投入。",
                    "thread_id": "test-api",
                    "export_artifacts": False,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["thread_id"], "test-api")
            self.assertIn("final_report", payload)
            self.assertTrue(payload["final_report"])
            self.assertIn(payload["llm_backend"], {"deepseek", "local-fallback"})

    def test_upload_endpoint(self) -> None:
        tmp_root = ROOT / "test_artifacts" / f"upload-test-{uuid4().hex[:8]}"
        tmp_root.mkdir(parents=True, exist_ok=True)
        app = create_app(build_test_config(tmp_root, api_key=None))
        with TestClient(app) as client:
            pdf = fitz.open()
            page = pdf.new_page()
            page.insert_text((72, 72), "Apple revenue 400 EBITDA 120 risk warning")
            pdf_bytes = pdf.tobytes()
            pdf.close()
            response = client.post(
                "/api/v1/analyze-upload",
                data={"query": "请分析这份 Apple 财报 PDF 的核心风险。", "thread_id": "upload-test", "export_artifacts": "false"},
                files={"files": ("Apple_report.pdf", pdf_bytes, "application/pdf")},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["thread_id"], "upload-test")
            self.assertIn("Apple", payload["final_report"])

    def test_job_endpoints_and_auth(self) -> None:
        tmp_root = ROOT / "test_artifacts" / f"job-test-{uuid4().hex[:8]}"
        tmp_root.mkdir(parents=True, exist_ok=True)
        app = create_app(build_test_config(tmp_root, api_key="secret-key"))
        with TestClient(app) as client:
            unauthorized = client.get("/api/v1/config")
            self.assertEqual(unauthorized.status_code, 401)

            response = client.post(
                "/api/v1/jobs",
                headers={"X-API-Key": "secret-key"},
                json={
                    "query": "分析 Apple 2025 财报供应链附录风险，并输出报告。",
                    "thread_id": "job-test",
                    "export_artifacts": False,
                },
            )
            self.assertEqual(response.status_code, 202)
            created = response.json()
            self.assertIn(created["status"], {"pending", "running", "completed"})

            detail = client.get(f"/api/v1/jobs/{created['job_id']}", headers={"X-API-Key": "secret-key"})
            self.assertEqual(detail.status_code, 200)
            job_payload = detail.json()
            self.assertEqual(job_payload["job_id"], created["job_id"])
            for _ in range(20):
                if job_payload["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.05)
                detail = client.get(f"/api/v1/jobs/{created['job_id']}", headers={"X-API-Key": "secret-key"})
                job_payload = detail.json()
            self.assertIn(job_payload["status"], {"completed", "failed"})

            listing = client.get("/api/v1/jobs", headers={"X-API-Key": "secret-key"})
            self.assertEqual(listing.status_code, 200)
            self.assertGreaterEqual(len(listing.json()), 1)


if __name__ == "__main__":
    unittest.main()
