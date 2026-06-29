from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from ..config import AppConfig
from ..logging_utils import configure_logging, request_logging_middleware
from ..service import FinanceAnalysisService
from .auth import build_api_key_dependency
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    JobResponse,
    SubmitJobRequest,
    SubmitJobResponse,
)


def create_app(config: AppConfig | None = None) -> FastAPI:
    configure_logging()
    app_config = config or AppConfig.from_env()
    service = FinanceAnalysisService(app_config)
    auth_dependency = build_api_key_dependency(app_config.api_key)

    app = FastAPI(
        title="Real-finan API",
        version="0.3.0",
        description="Deployable multi-agent finance research and compliance API powered by LangGraph and DeepSeek.",
    )
    app.middleware("http")(request_logging_middleware)

    static_dir = Path(__file__).resolve().parent.parent.parent.parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    from starlette.responses import Response

    @app.middleware("http")
    async def _cache_control(request, call_next):
        response: Response = await call_next(request)
        if request.url.path.startswith("/static"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/static/index.html")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        backend = "deepseek" if app_config.llm.api_key else "local-fallback"
        return HealthResponse(status="ok", llm_backend=backend)

    @app.get("/api/v1/config")
    def get_config(_: None = Depends(auth_dependency)) -> dict:
        return {
            "output_dir": str(app_config.output_dir),
            "upload_dir": str(app_config.upload_dir),
            "db_path": str(app_config.db_path),
            "database_url": app_config.database_url,
            "host": app_config.host,
            "port": app_config.port,
            "deepseek_model": app_config.llm.model,
            "deepseek_enabled": bool(app_config.llm.api_key),
            "api_key_enabled": bool(app_config.api_key),
            "redis_enabled": bool(app_config.redis_url),
            "neo4j_enabled": bool(app_config.neo4j_uri),
            "market_data_provider": app_config.market_data_provider,
        }

    @app.post("/api/v1/analyze", response_model=AnalyzeResponse)
    def analyze(payload: AnalyzeRequest, _: None = Depends(auth_dependency)) -> AnalyzeResponse:
        response = service.analyze(
            query=payload.query,
            thread_id=payload.thread_id,
            export_artifacts=payload.export_artifacts,
        )
        result = response["result"]
        return AnalyzeResponse(
            thread_id=response["thread_id"],
            llm_backend=response["llm_backend"],
            final_report=result["final_report"],
            executive_summary=result.get("executive_summary"),
            compliance_summary=result.get("compliance_summary"),
            audit_log=result.get("audit_log", []),
            artifacts=response["artifacts"],
            state=result,
            chart_data=result.get("chart_data"),
        )

    @app.post("/api/v1/analyze-upload", response_model=AnalyzeResponse)
    async def analyze_upload(
        query: str = Form(...),
        thread_id: str | None = Form(default=None),
        export_artifacts: bool = Form(default=True),
        files: list[UploadFile] = File(...),
        _: None = Depends(auth_dependency),
    ) -> AnalyzeResponse:
        saved_paths = service.save_uploaded_files([(upload.filename or "document.pdf", await upload.read()) for upload in files])
        response = service.analyze(
            query=query,
            thread_id=thread_id,
            export_artifacts=export_artifacts,
            document_paths=saved_paths,
        )
        result = response["result"]
        return AnalyzeResponse(
            thread_id=response["thread_id"],
            llm_backend=response["llm_backend"],
            final_report=result["final_report"],
            executive_summary=result.get("executive_summary"),
            compliance_summary=result.get("compliance_summary"),
            audit_log=result.get("audit_log", []),
            artifacts=response["artifacts"],
            state=result,
            chart_data=result.get("chart_data"),
        )

    @app.post("/api/v1/jobs", response_model=SubmitJobResponse, status_code=202)
    def submit_job(
        payload: SubmitJobRequest,
        background_tasks: BackgroundTasks,
        _: None = Depends(auth_dependency),
    ) -> SubmitJobResponse:
        created = service.submit_job(query=payload.query, thread_id=payload.thread_id)
        queued = service.enqueue_job(
            created["job_id"],
            payload.query,
            created["thread_id"],
            payload.export_artifacts,
        )
        if not queued:
            background_tasks.add_task(
                service.run_job,
                created["job_id"],
                payload.query,
                created["thread_id"],
                payload.export_artifacts,
            )
        return SubmitJobResponse(**created, queue_backend="redis" if queued else "background-task")

    @app.post("/api/v1/jobs/upload", response_model=SubmitJobResponse, status_code=202)
    async def submit_upload_job(
        background_tasks: BackgroundTasks,
        query: str = Form(...),
        thread_id: str | None = Form(default=None),
        export_artifacts: bool = Form(default=True),
        files: list[UploadFile] = File(...),
        _: None = Depends(auth_dependency),
    ) -> SubmitJobResponse:
        saved_paths = service.save_uploaded_files([(upload.filename or "document.pdf", await upload.read()) for upload in files])
        created = service.submit_job(query=query, thread_id=thread_id)
        queued = service.enqueue_job(
            created["job_id"],
            query,
            created["thread_id"],
            export_artifacts,
            document_paths=saved_paths,
        )
        if not queued:
            background_tasks.add_task(
                service.run_job,
                created["job_id"],
                query,
                created["thread_id"],
                export_artifacts,
                saved_paths,
            )
        return SubmitJobResponse(**created, queue_backend="redis" if queued else "background-task")

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str, _: None = Depends(auth_dependency)) -> JobResponse:
        job = service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return JobResponse(**job)

    @app.get("/api/v1/jobs", response_model=list[JobResponse])
    def list_jobs(
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(auth_dependency),
    ) -> list[JobResponse]:
        return [JobResponse(**job) for job in service.list_jobs(limit=limit)]

    return app


app = create_app()
