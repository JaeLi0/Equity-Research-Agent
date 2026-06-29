from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="User query for financial multi-agent analysis.")
    thread_id: Optional[str] = Field(default=None, description="Optional workflow thread id.")
    export_artifacts: bool = Field(default=True, description="Whether to persist report and state files.")


class AnalyzeResponse(BaseModel):
    thread_id: str
    llm_backend: str
    final_report: str
    executive_summary: Optional[str] = None
    compliance_summary: Optional[str] = None
    audit_log: list[dict[str, Any]]
    artifacts: dict[str, str]
    state: dict[str, Any]
    chart_data: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    llm_backend: str


class SubmitJobRequest(BaseModel):
    query: str = Field(..., description="User query for asynchronous financial analysis.")
    thread_id: Optional[str] = Field(default=None, description="Optional workflow thread id.")
    export_artifacts: bool = Field(default=True, description="Whether the background job should export files.")


class SubmitJobResponse(BaseModel):
    job_id: str
    thread_id: str
    status: str
    queue_backend: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    thread_id: str
    query: str
    status: str
    llm_backend: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
