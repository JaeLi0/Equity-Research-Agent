<div align="right">
  <strong>English</strong> | <a href="README_CN.md">中文</a>
</div>

# 🏦 Real-Finan — Enterprise Multi-Agent Financial Analysis System

A production-ready, LangGraph-powered multi-agent system that automates institutional-grade equity research. Seven specialized agents collaborate in a stateful pipeline — from company identification and multi-source data fusion to quantitative metrics, sentiment analysis, risk scoring, compliance review, and final report synthesis.

**Runs fully without an API key** — a built-in demo mode completes the entire pipeline and generates a structured report, making it easy to evaluate locally.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI REST Layer                       │
│   /analyze  |  /analyze-upload  |  /jobs/*  |  /health     │
│   Optional X-API-Key auth  |  Request-ID logging middleware │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              FinanceAnalysisService  (service.py)            │
│   .analyze()  |  .submit_job()  |  .enqueue_job()           │
│   PDF parsing (PyMuPDF) → document_contexts                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│         FinanceMultiAgentSystem  (graph.py)                  │
│                                                              │
│   START → Supervisor → Retrieval ──────────────────────┐    │
│                            │                           │    │
│                      [data gap?]                       │    │
│                            │                           │    │
│                        Replanner ◄──── (retry ≥ 2:    │    │
│                            │             degraded)     │    │
│                            ▼                           │    │
│                    Quant Analyst → Psychologist        │    │
│                                        │               │    │
│                                    Critic              │    │
│                                        │               │    │
│              END ◄── Synthesizer ◄─────┘               │    │
│                          ▲                             │    │
│                          └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   LLM Client       Market Data      Knowledge Store
  DeepSeek API +   Yahoo / Alpha    NetworkX / Neo4j
  Auto-failover     Vantage
```

---

## ✨ Key Features

### 🤖 7-Agent Stateful Pipeline
A LangGraph `StateGraph` orchestrates seven specialized agents over a shared `FinanceState` TypedDict (30+ fields). Each agent reads only the fields it needs and writes back partial updates — LangGraph merges them automatically. `InMemorySaver` maintains checkpoint state across the full pipeline execution.

### 🔁 Three-Level Fault Tolerance
- **Retrieval gap detected** → Replanner triggers a supplementary search pass
- **Second failure** → `degraded_mode` activated; Synthesizer continues with available data and labels gaps explicitly
- **LLM unavailable** → `ResilientLLMClient` automatically switches to fallback; every output records `llm_backend` so consumers know exactly which path was taken

### 🔒 AST-Based Safe Formula Evaluator
Financial ratios (EBITDA Margin, R&D Intensity, Operating Margin) are computed via a custom `ast.NodeVisitor` with an allowlist of 12 safe AST node types — `Add`, `Sub`, `Mult`, `Div`, `Pow`, and primitives only. `eval()` is never called. Any unapproved node (e.g. `Call`, `Attribute`) raises `ValueError` at parse time.

### 🔌 Pluggable LLM Backend
`BaseLLMClient` defines a single `chat()` interface. `build_llm_client()` selects the implementation from environment variables at startup. Swapping from DeepSeek to any OpenAI-compatible endpoint, Azure OpenAI, or a locally hosted model requires only one new subclass — no changes to agent logic.

### 🏛️ Three-Layer Memory Architecture
| Layer | Implementation | Scope |
|---|---|---|
| Session Memory | In-process snapshot per agent step | Single analysis run |
| Knowledge Graph | NetworkX (default) / Neo4j (optional) | Company entities, metrics, risk nodes |
| Reasoning Memory | Audit event log per agent | Full auditability |

### 📊 11-Chapter Institutional Report
Each run produces a Markdown research report with: Executive Summary · Analytical Framework · Company Profiles · Financial Performance · Industry Context · SWOT · Scenario Analysis (Base / Bull / Bear) · Investment Thesis · Peer Comparison · Compliance Review · Methodology & Disclaimer — plus a structured JSON chart payload and a full agent audit trail.

### 🔭 Full Observability
Every analysis generates three artifacts in `outputs/`:
- `*_report.md` — final research report
- `*_audit.json` — per-agent execution log with status and detail
- `*_state.json` — complete `FinanceState` snapshot for debugging

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph `StateGraph` + `ConditionalEdges` |
| API | FastAPI + Uvicorn |
| LLM | DeepSeek Chat (pluggable via `BaseLLMClient`) |
| Market Data | yfinance (Yahoo Finance) / Alpha Vantage |
| PDF Parsing | PyMuPDF (fitz) |
| Knowledge Graph | NetworkX (in-memory) / Neo4j (optional) |
| Task Queue | Redis + RQ / FastAPI `BackgroundTasks` fallback |
| Database | SQLAlchemy ORM → SQLite (dev) / PostgreSQL (prod) |
| Containerization | Docker + Docker Compose (5-service stack) |

---

## 🚀 Quick Start

### Option 1 — CLI Demo (no API key required)

```bash
git clone <repo-url> && cd Multi-Agent-project
pip install -r requirements.txt
python run_demo.py
```

Output files are written to `outputs/`. Add `--json` to see the full state dump.

### Option 2 — API Server

```bash
# Optional: set your DeepSeek API key for real LLM analysis
export DEEPSEEK_API_KEY="sk-..."

python start_api.py
# API available at http://127.0.0.1:8000
# Swagger UI at http://127.0.0.1:8000/docs
```

Run an analysis:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare Apple and Microsoft supply chain risk and R&D investment"}'
```

Upload a PDF annual report:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze-upload \
  -F "query=Analyze the core risks in this annual report" \
  -F "files=@/path/to/annual_report.pdf"
```

### Option 3 — API Server (local, no Docker)

```bash
export DEEPSEEK_API_KEY="sk-..."   # optional
python start_api.py
```

---

## 🐳 Docker Deployment

### Single container

```bash
# Build
docker build -t real-finan-api .

# Run (without Redis/Neo4j/PostgreSQL)
docker run -p 8000:8000 \
  -e DEEPSEEK_API_KEY="sk-..." \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/data:/app/data \
  real-finan-api
```

### Full stack — docker compose (recommended)

```bash
cp .env.example .env
# Set DEEPSEEK_API_KEY in .env if needed

docker compose up --build
```

Starts five services in one command:

| Service | Description |
|---|---|
| `real-finan-api` | FastAPI server on port 8000 |
| `real-finan-worker` | Redis queue worker for async jobs |
| `postgres` | Job persistence (PostgreSQL 16) |
| `redis` | Task queue (Redis 7) |
| `neo4j` | Knowledge graph (Neo4j 5, ports 7474 / 7687) |

### Async worker (standalone)

To run the worker separately against an existing Redis instance:

```bash
docker run --rm \
  -e DEEPSEEK_API_KEY="sk-..." \
  -e MAS_REDIS_URL="redis://host.docker.internal:6379/0" \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/data:/app/data \
  real-finan-api python start_worker.py
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check (no auth required) |
| `GET` | `/api/v1/config` | Active configuration |
| `POST` | `/api/v1/analyze` | Synchronous analysis |
| `POST` | `/api/v1/analyze-upload` | Upload PDF + synchronous analysis |
| `POST` | `/api/v1/jobs` | Submit async job |
| `POST` | `/api/v1/jobs/upload` | Upload PDF + submit async job |
| `GET` | `/api/v1/jobs/{job_id}` | Job status |
| `GET` | `/api/v1/jobs` | List recent jobs |

**Request body for `/api/v1/analyze`:**
```json
{
  "query": "Compare Apple and Microsoft supply chain risk",
  "thread_id": "run-001",
  "export_artifacts": true
}
```

**Authentication:** Set `MAS_API_KEY` in your environment to enable `X-API-Key` header auth on all `/api/v1/*` endpoints. `/health` remains unauthenticated.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and set values as needed:

```bash
# LLM (required for real analysis; omit to run in demo mode)
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# API server
MAS_HOST=127.0.0.1
MAS_PORT=8000
MAS_API_KEY=               # leave blank to disable auth

# Storage
MAS_OUTPUT_DIR=outputs
MAS_DB_PATH=data/real_finan.db

# Optional: PostgreSQL (defaults to SQLite)
MAS_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/real_finan

# Optional: Redis (falls back to FastAPI BackgroundTasks)
MAS_REDIS_URL=redis://localhost:6379/0

# Optional: Neo4j (falls back to in-memory NetworkX graph)
MAS_NEO4J_URI=bolt://localhost:7687
MAS_NEO4J_USERNAME=neo4j
MAS_NEO4J_PASSWORD=neo4j_password

# Market data
MAS_MARKET_DATA_PROVIDER=yahoo   # yahoo | alphavantage
ALPHAVANTAGE_API_KEY=            # only needed for alphavantage
```

Every optional dependency (Redis, Neo4j, PostgreSQL, DeepSeek) has an automatic fallback — the system runs with zero external services.

---

## 📁 Project Structure

```
Multi-Agent-project/
├── run_demo.py              # CLI entry point
├── start_api.py             # API server entry point
├── start_worker.py          # Async worker entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── src/real_finan/
    ├── graph.py             # ⭐ StateGraph assembly + routing logic
    ├── agents.py            # ⭐ All 7 agent implementations (753 lines)
    ├── tools.py             # ⭐ AST evaluator, sentiment, scenario analysis
    ├── state.py             # FinanceState TypedDict (30+ fields)
    ├── llm.py               # LLM client layer (DeepSeek + fallback + resilient)
    ├── config.py            # Immutable AppConfig from environment
    ├── service.py           # Business orchestration layer
    ├── market_data.py       # yfinance / Alpha Vantage client
    ├── documents.py         # PDF parsing + metric extraction
    ├── knowledge_store.py   # NetworkX / Neo4j knowledge graph
    ├── memory.py            # Session, reasoning, and KG memory
    ├── database.py          # SQLAlchemy ORM + job repository
    ├── queueing.py          # Redis BLPOP/RPUSH queue manager
    ├── reporting.py         # Artifact export
    ├── api/
    │   ├── app.py           # FastAPI factory + route definitions
    │   ├── schemas.py       # Pydantic request/response models
    │   └── auth.py          # API key dependency
    └── data/
        └── sample_financial_data.py   # Built-in Apple & Microsoft data
```

---

## 🧪 Running Tests

```bash
python -m pytest tests/test_system.py -v
```

Five test cases cover: end-to-end report generation, replanner path + artifact export, synchronous API endpoint, PDF upload endpoint, and async job submission with authentication.

---

## 🖥️ Screenshots

<img width="2314" height="1498" alt="image" src="https://github.com/user-attachments/assets/1c0afc01-bf68-41b8-8192-4e5c8f7d265e" />
<img width="1972" height="1279" alt="image" src="https://github.com/user-attachments/assets/3799c187-2405-4551-bc19-cb764c5a5b76" />
<img width="1980" height="1279" alt="image" src="https://github.com/user-attachments/assets/20d2284b-2f98-4673-b734-54a53d574907" />

---

## 🤖 Agent Roles

| Agent | Responsibility |
|---|---|
| **Supervisor** | Extracts company names (4-level strategy: sample data → alias map → LLM extraction → PDF filename fallback), generates task brief and analysis dimensions |
| **Retrieval** | Fuses sample data + real-time market quotes + PDF-extracted metrics; generates company profiles via LLM; writes to Knowledge Store |
| **Quantitative Analyst** | Computes EBITDA Margin, R&D Intensity, Operating Margin via AST evaluator; integrates live PE / market cap / 52-week position; generates peer comparison |
| **Psychologist** | Dual-layer sentiment: rule-based keyword engine (positive/negative word counts) + LLM deep analysis (tone / confidence score / key themes / risk flags) |
| **Critic** | Five-dimensional risk scoring (Financial / Operational / Market / Regulatory / Supply Chain) with factor-driven calibration; LLM compliance review |
| **Replanner** | Increments retry counter; on first failure sets `appendix_search_done=True` to redirect Retrieval; on second failure activates `degraded_mode` |
| **Synthesizer** | Assembles 11-chapter Markdown report: SWOT, scenario analysis (Base/Bull/Bear), investment thesis, chart data; writes final audit log |

---

## 🏛️ Design Notes

### 1. Orchestration

Normal path: `Supervisor → Retrieval → Quant → Psychologist → Critic → Synthesizer`

When a data gap is detected after Retrieval or Quant, control passes to Replanner:
- **1st failure** — switches to appendix supplementary retrieval strategy
- **2nd failure** — activates degraded mode; pipeline continues and produces a report with explicit gap annotations

### 2. Three-Layer Memory

- **SessionMemory** — saves a full state snapshot after each agent step
- **KnowledgeGraphMemory** — ingests company entities, metrics, risk nodes, and appendix fields into a graph structure (NetworkX or Neo4j)
- **ReasoningMemory** — records one audit event per agent step for full traceability

### 3. Security

Financial formulas are evaluated by an AST-based allowlist evaluator (`tools.py`) — only basic arithmetic nodes are permitted. `eval()` is never called, making arbitrary code execution physically impossible.

### 4. Output Artifacts

Each run writes three files to the output directory:
- `*_report.md` — final research report
- `*_audit.json` — agent execution audit trail
- `*_state.json` — complete workflow final state

### 5. Service Enhancements

Beyond the core pipeline, the system adds:
- SQLite / PostgreSQL job persistence via SQLAlchemy ORM
- Async background analysis jobs with status polling
- Optional `X-API-Key` authentication on all `/api/v1/*` endpoints
- Per-request logging with `X-Request-Id` response headers
- Real PDF upload and parsing
- Live market data integration (Yahoo Finance / Alpha Vantage)
- Neo4j knowledge graph support
- Redis queue + independent worker process
