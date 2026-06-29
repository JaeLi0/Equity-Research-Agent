from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .config import AppConfig
from .database import JobRepository
from .documents import parse_pdf_document
from .graph import FinanceMultiAgentSystem
from .llm import build_llm_client
from .queueing import RedisQueueManager
from .reporting import export_run_artifacts


class FinanceAnalysisService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.repository = JobRepository(config.database_url, db_path=config.db_path)

    def analyze(
        self,
        query: str,
        thread_id: str | None = None,
        export_artifacts: bool = True,
        document_paths: list[str] | None = None,
    ) -> dict:
        actual_thread_id = thread_id or f"run-{uuid4().hex[:8]}"
        llm_client = build_llm_client(self.config.llm)
        system = FinanceMultiAgentSystem(llm_client=llm_client, app_config=self.config)
        document_contexts = [parse_pdf_document(Path(path)) for path in (document_paths or [])]
        result = system.run(query, thread_id=actual_thread_id, document_contexts=document_contexts)

        artifacts: dict[str, str] = {}
        if export_artifacts:
            artifacts = export_run_artifacts(
                result=result,
                output_dir=self.config.output_dir,
                thread_id=actual_thread_id,
            )

        return {
            "thread_id": actual_thread_id,
            "llm_backend": result.get("llm_backend", llm_client.backend_name),
            "result": result,
            "artifacts": artifacts,
        }

    def submit_job(self, query: str, thread_id: str | None = None) -> dict:
        actual_thread_id = thread_id or f"run-{uuid4().hex[:8]}"
        job_id = f"job-{uuid4().hex[:10]}"
        self.repository.create_job(job_id=job_id, thread_id=actual_thread_id, query=query)
        return {"job_id": job_id, "thread_id": actual_thread_id, "status": "pending"}

    def enqueue_job(
        self,
        job_id: str,
        query: str,
        thread_id: str,
        export_artifacts: bool = True,
        document_paths: list[str] | None = None,
    ) -> bool:
        if not self.config.redis_url:
            return False
        queue = RedisQueueManager(self.config.redis_url, self.config.redis_queue_name)
        queue.enqueue(
            {
                "job_id": job_id,
                "query": query,
                "thread_id": thread_id,
                "export_artifacts": export_artifacts,
                "document_paths": document_paths or [],
            }
        )
        return True

    def run_job(
        self,
        job_id: str,
        query: str,
        thread_id: str,
        export_artifacts: bool = True,
        document_paths: list[str] | None = None,
    ) -> None:
        self.repository.update_job_status(job_id=job_id, status="running")
        try:
            response = self.analyze(
                query=query,
                thread_id=thread_id,
                export_artifacts=export_artifacts,
                document_paths=document_paths,
            )
            self.repository.update_job_status(
                job_id=job_id,
                status="completed",
                llm_backend=response["llm_backend"],
                result=response["result"],
                artifacts=response["artifacts"],
            )
        except Exception as exc:
            self.repository.update_job_status(
                job_id=job_id,
                status="failed",
                error_message=str(exc),
            )
            raise

    def get_job(self, job_id: str) -> dict | None:
        return self.repository.get_job(job_id)

    def list_jobs(self, limit: int = 20) -> list[dict]:
        return self.repository.list_jobs(limit=limit)

    def save_uploaded_files(self, files: list[tuple[str, bytes]]) -> list[str]:
        self.config.upload_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[str] = []
        for filename, content in files:
            unique_name = f"{uuid4().hex[:8]}_{filename}"
            target_path = self.config.upload_dir / unique_name
            target_path.write_bytes(content)
            saved_paths.append(str(target_path))
        return saved_paths
