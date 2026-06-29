<div align="right">
  <strong>中文</strong> | <a href="README.md">English</a>
</div>

# 🏦 Real-Finan — 企业级多智能体金融分析系统

基于 LangGraph 状态图编排的多 Agent 金融分析系统。七个专业化 Agent 通过共享状态协同完成完整投研流程——从公司识别、多源数据融合、五维量化指标计算、管理层情绪分析，到风险评分、合规审计，最终输出含 SWOT 拆解、情景推演（Base / Bull / Bear）和投资论点的机构级研究报告。

**无需任何 API Key 即可跑通完整流水线** — 内置演示模式，零依赖生成完整报告，方便本地体验。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI REST 层                          │
│   /analyze  |  /analyze-upload  |  /jobs/*  |  /health     │
│   可选 X-API-Key 鉴权  |  Request-ID 请求日志中间件          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│           FinanceAnalysisService  (service.py)               │
│   .analyze()  |  .submit_job()  |  .enqueue_job()           │
│   PDF 解析 (PyMuPDF) → document_contexts                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│       FinanceMultiAgentSystem  (graph.py)                    │
│                                                              │
│  START → Supervisor → Retrieval ───────────────────────┐    │
│                           │                            │    │
│                     [数据缺口?]                         │    │
│                           │                            │    │
│                       Replanner ◄──── (重试≥2:         │    │
│                           │             降级模式)       │    │
│                           ▼                            │    │
│                   量化分析师 → Psychologist             │    │
│                                   │                    │    │
│                               Critic                   │    │
│                                   │                    │    │
│             END ◄── Synthesizer ◄─┘                    │    │
│                         ▲                              │    │
│                         └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   LLM 客户端        行情数据源          知识图谱
  DeepSeek API +   Yahoo / Alpha       NetworkX /
  自动容错切换       Vantage             Neo4j
```

---

## ✨ 核心特性

### 🤖 7 Agent 有状态流水线
LangGraph `StateGraph` 编排 7 个专业化 Agent，通过共享的 `FinanceState` TypedDict（30+ 字段）传递状态。每个 Agent 只读取所需字段，写回部分更新，框架自动合并。`InMemorySaver` 维护完整执行链路的 Checkpoint 状态。

### 🔁 三级容错机制
- **检索数据缺口** → Replanner 触发补充检索
- **二次仍不足** → 激活 `degraded_mode`，Synthesizer 继续生成并在报告中标注缺口
- **LLM 不可用** → `ResilientLLMClient` 自动切换 fallback 路径；每份输出均记录 `llm_backend` 字段，消费方可精确知晓本次分析所用的执行路径

### 🔒 AST 安全公式求值器
财务指标（EBITDA Margin、R&D Intensity、Operating Margin）通过自定义 `ast.NodeVisitor` 计算，白名单仅放行 12 种安全 AST 节点（加减乘除幂运算及常量）。`eval()` 从不被调用——任何未授权节点（如 `Call`、`Attribute`）在 AST 解析阶段直接抛 `ValueError`，物理隔绝代码注入风险。

### 🔌 可替换 LLM 后端
`BaseLLMClient` 定义统一的 `chat()` 接口，`build_llm_client()` 在启动时根据环境变量选择实现。将 DeepSeek 替换为任何 OpenAI 兼容接口、Azure OpenAI 或本地部署模型，只需新增一个子类，无需修改任何 Agent 逻辑。

### 🏛️ 三层记忆架构
| 层次 | 实现 | 作用域 |
|---|---|---|
| Session Memory | 进程内每步状态快照 | 单次分析 |
| 知识图谱 | NetworkX（默认）/ Neo4j（可选）| 公司实体、指标、风险节点 |
| Reasoning Memory | 每个 Agent 的审计事件日志 | 全链路可溯源 |

### 📊 机构级 11 章研究报告
每次运行产出一份 Markdown 研究报告，包含：执行摘要 · 分析框架 · 公司画像 · 财务表现 · 行业背景 · SWOT · 情景分析（Base / Bull / Bear）· 投资论点 · 同行对标 · 合规审计 · 方法论与免责声明——同时生成结构化图表 JSON 数据和完整 Agent 审计日志。

### 🔭 全链路可观测
每次分析在 `outputs/` 目录生成三类产物：
- `*_report.md` — 最终研究报告
- `*_audit.json` — 各 Agent 执行状态与细节
- `*_state.json` — 完整 `FinanceState` 快照，方便回溯调试

---

## 🛠️ 技术栈

| 层次 | 技术选型 |
|---|---|
| Agent 编排 | LangGraph `StateGraph` + `ConditionalEdges` |
| API 框架 | FastAPI + Uvicorn |
| 大模型 | DeepSeek Chat（通过 `BaseLLMClient` 可替换）|
| 行情数据 | yfinance（Yahoo Finance）/ Alpha Vantage |
| PDF 解析 | PyMuPDF (fitz) |
| 知识图谱 | NetworkX（内存）/ Neo4j（可选）|
| 任务队列 | Redis + RQ / FastAPI `BackgroundTasks` 降级 |
| 数据库 | SQLAlchemy ORM → SQLite（开发）/ PostgreSQL（生产）|
| 容器化 | Docker + Docker Compose（5 服务编排）|

---

## 🚀 快速开始

### 方式一 — CLI 演示（无需 API Key）

```bash
git clone <repo-url> && cd Multi-Agent-project
pip install -r requirements.txt
python run_demo.py
```

报告文件输出到 `outputs/` 目录。加 `--json` 参数可输出完整 state 快照。

### 方式二 — API 服务

```bash
# 可选：配置 DeepSeek API Key 启用真实 LLM 分析
export DEEPSEEK_API_KEY="sk-..."

python start_api.py
# API 地址：http://127.0.0.1:8000
# Swagger 文档：http://127.0.0.1:8000/docs
```

发起分析请求：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "对比分析 Apple 与 Microsoft 的供应链风险和研发投入"}'
```

上传 PDF 年报分析：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze-upload \
  -F "query=分析这份年报的核心财务指标和风险" \
  -F "files=@/path/to/annual_report.pdf"
```

### 方式三 — API 服务（本地，不用 Docker）

```bash
export DEEPSEEK_API_KEY="sk-..."   # 可选
python start_api.py
```

---

## 🐳 Docker 部署

### 单容器运行

```bash
# 构建镜像
docker build -t real-finan-api .

# 运行（不带 Redis/Neo4j/PostgreSQL）
docker run -p 8000:8000 \
  -e DEEPSEEK_API_KEY="sk-..." \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/data:/app/data \
  real-finan-api
```

### 完整服务栈 — docker compose（推荐）

```bash
cp .env.example .env
# 按需填入 DEEPSEEK_API_KEY

docker compose up --build
```

一键启动五个服务：

| 服务 | 说明 |
|---|---|
| `real-finan-api` | FastAPI 服务，端口 8000 |
| `real-finan-worker` | Redis 队列消费 Worker |
| `postgres` | 任务持久化（PostgreSQL 16）|
| `redis` | 任务队列（Redis 7）|
| `neo4j` | 知识图谱（Neo4j 5，端口 7474 / 7687）|

### 独立启动 Worker

```bash
docker run --rm \
  -e DEEPSEEK_API_KEY="sk-..." \
  -e MAS_REDIS_URL="redis://host.docker.internal:6379/0" \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/data:/app/data \
  real-finan-api python start_worker.py
```

---

## 📡 API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/health` | 健康检查（无需鉴权）|
| `GET` | `/api/v1/config` | 当前配置信息 |
| `POST` | `/api/v1/analyze` | 同步分析 |
| `POST` | `/api/v1/analyze-upload` | 上传 PDF + 同步分析 |
| `POST` | `/api/v1/jobs` | 提交异步任务 |
| `POST` | `/api/v1/jobs/upload` | 上传 PDF + 提交异步任务 |
| `GET` | `/api/v1/jobs/{job_id}` | 查询任务状态 |
| `GET` | `/api/v1/jobs` | 列出近期任务 |

**`/api/v1/analyze` 请求体示例：**
```json
{
  "query": "对比分析 Apple 与 Microsoft 的供应链风险",
  "thread_id": "run-001",
  "export_artifacts": true
}
```

**鉴权：** 设置 `MAS_API_KEY` 环境变量后，所有 `/api/v1/*` 接口需在请求头中携带 `X-API-Key`。`/health` 始终匿名可访问。

---

## ⚙️ 配置说明

复制 `.env.example` 为 `.env`，按需修改：

```bash
# LLM 配置（不填则以演示模式运行）
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# API 服务
MAS_HOST=127.0.0.1
MAS_PORT=8000
MAS_API_KEY=               # 留空则跳过鉴权

# 存储
MAS_OUTPUT_DIR=outputs
MAS_DB_PATH=data/real_finan.db

# 可选：PostgreSQL（不填则使用 SQLite）
MAS_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/real_finan

# 可选：Redis（不填则降级为 FastAPI BackgroundTasks）
MAS_REDIS_URL=redis://localhost:6379/0

# 可选：Neo4j（不填则使用内存 NetworkX 图）
MAS_NEO4J_URI=bolt://localhost:7687
MAS_NEO4J_USERNAME=neo4j
MAS_NEO4J_PASSWORD=neo4j_password

# 行情数据
MAS_MARKET_DATA_PROVIDER=yahoo   # yahoo | alphavantage
ALPHAVANTAGE_API_KEY=            # 仅 alphavantage 模式需要
```

所有可选依赖（Redis、Neo4j、PostgreSQL、DeepSeek）均有自动降级策略，系统在零外部服务的情况下也能完整运行。

---

## 📁 项目结构

```
Multi-Agent-project/
├── run_demo.py              # CLI 演示入口
├── start_api.py             # API 服务入口
├── start_worker.py          # 异步 Worker 入口
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── src/real_finan/
    ├── graph.py             # ⭐ StateGraph 构建 + 路由逻辑
    ├── agents.py            # ⭐ 7 个 Agent 完整实现（753 行）
    ├── tools.py             # ⭐ AST 求值器、情绪分析、情景推演
    ├── state.py             # FinanceState TypedDict（30+ 字段）
    ├── llm.py               # LLM 客户端层（DeepSeek + 容错代理）
    ├── config.py            # 不可变 AppConfig，从环境变量加载
    ├── service.py           # 业务编排层
    ├── market_data.py       # yfinance / Alpha Vantage 行情客户端
    ├── documents.py         # PDF 解析 + 财务指标提取
    ├── knowledge_store.py   # NetworkX / Neo4j 知识图谱
    ├── memory.py            # Session、Reasoning、KG 记忆层
    ├── database.py          # SQLAlchemy ORM + 任务仓库
    ├── queueing.py          # Redis BLPOP/RPUSH 队列管理
    ├── reporting.py         # 产物导出
    ├── api/
    │   ├── app.py           # FastAPI 工厂函数 + 路由定义
    │   ├── schemas.py       # Pydantic 请求/响应模型
    │   └── auth.py          # API Key 鉴权依赖
    └── data/
        └── sample_financial_data.py   # 内置 Apple & Microsoft 样本数据
```

---

## 🧪 运行测试

```bash
python -m pytest tests/test_system.py -v
```

覆盖五个测试场景：端到端报告生成、重规划路径 + 产物导出、同步 API 端点、PDF 上传端点、异步任务提交与鉴权。

---

## 🖥️ 界面展示

> _截图待添加_

---

## 🤖 系统角色

| Agent | 职责 |
|---|---|
| **Supervisor** | 四级公司名提取策略（样本数据匹配 → 别名表 → LLM 提取 → PDF 文件名回退），生成任务概述和分析维度 |
| **Retrieval** | 融合样本数据 + 实时行情 + PDF 提取指标，LLM 生成企业画像，写入知识图谱 |
| **量化分析师** | AST 求值器计算 EBITDA Margin / R&D Intensity / Operating Margin，集成实时 PE / 市值 / 52 周位置，LLM 生成同行对标 |
| **Psychologist** | 双层情绪分析——规则引擎（正/负面词库计数）+ LLM 深度分析（语气 / 信心评分 / 关键主题 / 风险标记）|
| **Critic** | 五维风险评分（财务 / 运营 / 市场 / 监管 / 供应链），因子驱动校准；LLM 合规审计 |
| **Replanner** | 递增重试计数；第一次失败设置 `appendix_search_done=True` 触发补检索；第二次失败激活 `degraded_mode` |
| **Synthesizer** | 组装 11 章 Markdown 报告（SWOT / 情景推演 / 投资论点 / 图表数据），写入最终审计日志 |

---

## 🏛️ 设计说明

### 1. 编排方式

正常路径：`Supervisor → Retrieval → 量化分析师 → Psychologist → Critic → Synthesizer`

当 Retrieval 或 Quant 阶段检测到数据缺口时，控制流进入 Replanner：
- **第一次失败** — 切换为附录补充检索策略
- **第二次失败** — 激活降级模式，流水线继续执行，报告中明确标注数据缺口

### 2. 三层记忆

- **SessionMemory** — 每个 Agent 执行后保存完整状态快照
- **KnowledgeGraphMemory** — 将公司实体、指标、风险节点、附录字段注入图结构（NetworkX 或 Neo4j）
- **ReasoningMemory** — 每个 Agent 步骤记录一条审计事件，支持全链路溯源

### 3. 安全性

财务公式通过 AST 白名单求值器执行（`tools.py`），仅允许基础算术 AST 节点，`eval()` 从不被调用，物理上不可能执行任意代码。

### 4. 产物输出

每次运行在输出目录生成三类文件：
- `*_report.md` — 最终研究报告
- `*_audit.json` — Agent 执行审计日志
- `*_state.json` — 完整工作流最终状态快照

### 5. 服务化增强

核心流水线之外，系统还提供：
- SQLite / PostgreSQL 作业持久化（SQLAlchemy ORM）
- 异步后台分析任务 + 状态轮询接口
- 可选 `X-API-Key` 鉴权（所有 `/api/v1/*` 接口）
- 请求级日志与 `X-Request-Id` 响应头
- 真实 PDF 上传解析
- 实时行情数据接入（Yahoo Finance / Alpha Vantage）
- Neo4j 知识图谱支持
- Redis 队列 + 独立 Worker 进程
