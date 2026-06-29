from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

try:
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:  # pragma: no cover
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver

from .config import AppConfig
from .agents import AgentRuntime
from .knowledge_store import InMemoryKnowledgeStore, Neo4jKnowledgeStore
from .llm import BaseLLMClient, build_llm_client
from .market_data import MarketDataClient
from .memory import ReasoningMemory, SessionMemory
from .state import FinanceState


def route_after_retrieval(state: FinanceState) -> str:
    return "replanner" if state.get("replan_reason") else "quant"


def route_after_quant(state: FinanceState) -> str:
    return "replanner" if state.get("replan_reason") else "psychologist"


def route_after_critic(state: FinanceState) -> str:
    findings = state.get("compliance_findings", [])
    return "synthesizer" if not findings else "synthesizer"


def route_after_replanner(state: FinanceState) -> str:
    return "synthesizer" if state.get("degraded_mode") else "retrieval"


class FinanceMultiAgentSystem:
    def __init__(self, llm_client: BaseLLMClient | None = None, app_config: AppConfig | None = None) -> None:
        self.app_config = app_config or AppConfig.from_env()
        self.session_memory = SessionMemory()
        self.knowledge_memory = self._build_knowledge_store()
        self.reasoning_memory = ReasoningMemory()
        self.llm_client = llm_client or build_llm_client()
        self.market_data_client = MarketDataClient(
            provider=self.app_config.market_data_provider,
            alphavantage_api_key=self.app_config.alphavantage_api_key,
        )
        self.runtime = AgentRuntime(
            session_memory=self.session_memory,
            knowledge_memory=self.knowledge_memory,
            reasoning_memory=self.reasoning_memory,
            llm_client=self.llm_client,
            market_data_client=self.market_data_client,
        )
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _build_knowledge_store(self):
        if self.app_config.neo4j_uri and self.app_config.neo4j_username and self.app_config.neo4j_password:
            try:
                return Neo4jKnowledgeStore(
                    uri=self.app_config.neo4j_uri,
                    username=self.app_config.neo4j_username,
                    password=self.app_config.neo4j_password,
                )
            except Exception:
                return InMemoryKnowledgeStore()
        return InMemoryKnowledgeStore()

    def _build_graph(self):
        workflow = StateGraph(FinanceState)
        workflow.add_node("supervisor", self.runtime.supervisor)
        workflow.add_node("retrieval", self.runtime.retrieval)
        workflow.add_node("quant", self.runtime.quantitative_analyst)
        workflow.add_node("psychologist", self.runtime.psychologist)
        workflow.add_node("critic", self.runtime.critic)
        workflow.add_node("replanner", self.runtime.replanner)
        workflow.add_node("synthesizer", self.runtime.synthesizer)

        workflow.add_edge(START, "supervisor")
        workflow.add_edge("supervisor", "retrieval")
        workflow.add_conditional_edges(
            "retrieval",
            route_after_retrieval,
            {"quant": "quant", "replanner": "replanner"},
        )
        workflow.add_conditional_edges(
            "quant",
            route_after_quant,
            {"psychologist": "psychologist", "replanner": "replanner"},
        )
        workflow.add_edge("psychologist", "critic")
        workflow.add_conditional_edges(
            "critic",
            route_after_critic,
            {"synthesizer": "synthesizer"},
        )
        workflow.add_conditional_edges(
            "replanner",
            route_after_replanner,
            {"retrieval": "retrieval", "synthesizer": "synthesizer"},
        )
        workflow.add_edge("synthesizer", END)

        return workflow.compile(checkpointer=self.checkpointer)

    def run(
        self,
        query: str,
        thread_id: str = "demo-thread",
        document_contexts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        initial_state: FinanceState = {
            "query": query,
            "document_contexts": document_contexts or [],
            "audit_log": [],
            "reasoning_memory": [],
            "compliance_findings": [],
            "report_sections": [],
            "appendix_search_done": False,
            "retries": 0,
            "degraded_mode": False,
        }
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(initial_state, config=config)
        final_result = dict(result)
        final_result["thread_id"] = thread_id
        final_result["checkpoint_count"] = len(self.session_memory.checkpoints)
        final_result["llm_backend"] = self.llm_client.backend_name
        return final_result
