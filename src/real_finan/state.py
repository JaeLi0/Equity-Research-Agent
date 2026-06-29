from typing import Any, Optional

from typing_extensions import TypedDict


class AuditEvent(TypedDict):
    step: str
    status: str
    detail: str


class FinanceState(TypedDict, total=False):
    query: str
    companies: list[str]
    target_symbols: dict[str, str]
    plan: list[str]
    task_brief: str
    document_contexts: list[dict[str, Any]]
    retrieved_docs: dict[str, dict[str, Any]]
    market_snapshots: dict[str, dict[str, Any]]
    appendix_search_done: bool
    financial_metrics: dict[str, dict[str, float]]
    sentiment_analysis: dict[str, dict[str, Any]]
    compliance_findings: list[str]
    compliance_summary: str
    report_sections: list[str]
    executive_summary: str
    final_report: str
    llm_backend: str
    audit_log: list[AuditEvent]
    knowledge_snapshot: dict[str, Any]
    reasoning_memory: list[str]
    replan_reason: Optional[str]
    retries: int
    degraded_mode: bool
    # Enriched fields
    company_profiles: dict[str, str]
    swot_analysis: dict[str, dict[str, str]]
    risk_scores: dict[str, dict[str, float]]
    investment_thesis: dict[str, dict[str, str]]
    chart_data: dict[str, Any]
    peer_comparison: dict[str, Any]
