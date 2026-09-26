# 智能竞品分析助手

基于 **LangGraph + LangSmith** 的多 Agent 竞品分析系统。输入竞品名称，自动完成多维度调研、生成结构化对比报告。

---

## 核心功能

- **多领域支持**：软件产品 / 实体商品 / 服务，一套 Agent 逻辑适配多个垂直领域
- **多竞品对比**：支持 2~3 个竞品横向对比，输出对比矩阵、SWOT、选型建议
- **多 Agent 协作**：Planner / Collector / Analyzer / Writer 四节点协同
- **质量校验与重试**：Analyzer 后自动检查质量，不达标自动重新采集
- **RAG 记忆机制**：分析完成后报告自动索引，下次分析相似竞品时检索历史作为参考
- **实时进度推送**：SSE 流式显示每一步执行状态
- **完整评估体系**：LangSmith + 9 个自定义评估器，支持 baseline 对比
- **报告导出**：支持导出 Markdown 和 PDF
- **历史管理**：查看、删除历史报告

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + LangGraph + LangSmith |
| 前端 | Vue3 + TypeScript + Ant Design Vue |
| LLM | DeepSeek（可切换任意 OpenAI 兼容模型） |
| 搜索 | Tavily API |
| 向量检索 | Qdrant Cloud + BAAI/bge-small-zh-v1.5 |
| 长期记忆 | LangGraph InMemoryStore |
| 文档渲染 | Markdown + marked |
| PDF 导出 | html2canvas + jsPDF |
| 状态持久化 | MemorySaver（图内）+ JSON 文件（图外） |

---

## 架构设计

### 多 Agent 协作流程

```
┌──────────────────────────────────────────────────────────────┐
│                      用户输入竞品名称                          │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │   MemoryRetriever      │  ← 检索历史报告
              │   （RAG 检索）           │    （Chroma）
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │       Planner          │  ← 拆解 4~5 个子任务
              │   （为每个竞品规划）      │
              └───────────┬────────────┘
                          ▼
         ┌────────────────────────────────┐
         │   对每个竞品循环处理               │
         │                                │
         │   ┌─────────────────────┐      │
         │   │  Collector（搜索）   │      │
         │   └──────────┬──────────┘      │
         │              ▼                 │
         │   ┌─────────────────────┐      │
         │   │  Analyzer（提炼）    │      │
         │   └──────────┬──────────┘      │
         │              ▼                 │
         │   ┌─────────────────────┐      │
         │   │  QualityCheck       │      │
         │   └──────────┬──────────┘      │
         │              │                 │
         │        ┌─────┴─────┐           │
         │        ▼           ▼           │
         │   不达标重试    达标继续           │
         │        │           │           │
         │        └─→ C       │           │
         │                    ▼           │
         │              下一子任务/竞品      │
         └────────────────┬───────────────┘
                          ▼
              ┌───────────────────────┐
              │     对比模式判断        │
              └───────┬───────┬───────┘
                      │       │
              单竞品 ▼       ▼ 多竞品
          ┌────────────┐  ┌────────────────────┐
          │   Writer   │  │ ComparisonAnalyst  │
          │ （生成报告） │  │ （对齐对比维度）       │
          └──────┬─────┘  └─────────┬──────────┘
                 │                  ▼
                 │       ┌────────────────────┐
                 │       │  ComparisonWriter  │
                 │       │ （生成对比报告）      │
                 │       └─────────┬──────────┘
                 │                 │
                 └────────┬────────┘
                          ▼
              ┌────────────────────────┐
              │   ReportIndexer        │  → 报告入库
              │   （Qdrant 写入）       │    更新用户记忆
              └───────────┬────────────┘
                          ▼
                  ┌───────────────┐
                  │   返回报告     │
                  └───────────────┘
```

FastAPI SSE 实时推送 + LangSmith 追踪

### 各 Agent 职责

| Agent | 输入 | 输出 |
|-------|------|------|
| **MemoryRetriever** | 竞品名称 | 历史相关报告片段 + 用户偏好 |
| **Planner** | 竞品名称、行业、领域、历史上下文 | 4~5 个子任务 |
| **Collector** | 当前子任务 | 原始搜索结果 + 来源列表 |
| **Analyzer** | 原始搜索结果、历史上下文 | Markdown 格式的 TaskSummary |
| **QualityCheck** | TaskSummary | 通过 / 重试判断 |
| **Writer** | 所有 TaskSummary | 完整 Markdown 报告 |
| **ComparisonAnalyst** | 多竞品的所有 TaskSummary | 对比矩阵 + 洞察 |
| **ComparisonWriter** | 对比矩阵 + 洞察 | 对比报告 |
| **ReportIndexer** | 最终报告 | 按标题分块索引到 Qdrant + 更新用户记忆 |

---

## RAG 与记忆机制

本项目引入基于 **Qdrant Cloud** 的 RAG（检索增强生成）和 Memory 机制，让 Agent 具备跨会话的"记忆"能力。

### 工作原理

1. **报告分块**：分析完成后，`ReportIndexer` 节点用 `MarkdownHeaderTextSplitter` 按 `#`/`##`/`###` 标题将报告切分为语义完整的章节块
2. **元数据索引**：每个块携带 `competitor`、`section`、`chunk_index`、`report_id` 四个元数据字段，其中 `competitor` 创建为 keyword 索引
3. **向量入库**：分块内容经 `BAAI/bge-small-zh-v1.5` 嵌入后写入 Qdrant Cloud
4. **历史检索**：分析新竞品时，`MemoryRetriever` 节点用 metadata filter 限定竞品范围，检索 Top-5 相似章节块
5. **上下文注入**：检索到的章节内容注入 Planner 和 Analyzer 的 Prompt，作为分析参考
6. **偏好记忆**：使用 `InMemoryStore` 记录用户分析偏好，跨会话共享

### 工作流变化

```
START → MemoryRetriever → Planner → Collector → Analyzer
      → QualityCheck → (Writer | ComparisonWriter)
      → ReportIndexer → END
```

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 向量库 | Qdrant Cloud | 元数据过滤强、gRPC 低延迟 |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 | 中文友好、模型轻量（约 80MB） |
| 记忆存储 | LangGraph InMemoryStore | 与 LangGraph 原生集成 |

---

## 数据存储

### 报告持久化：JSON 文件 + Qdrant 向量库

**存储位置**：

每个报告独立一个 JSON 文件，文件名为 `{report_id}.json`（8 位 UUID）。

### 数据隔离说明

**本项目为单用户本地工具**：

- 所有报告保存在 `backend/data/reports/` 目录下
- 没有登录、注册、user_id 等认证机制
- 前端"历史报告"页面展示的是该目录下全部 JSON 文件
- **删除 `backend/data/` 目录即可清空所有历史**

---

## 评估结果

使用 LangSmith 对 7 个评估样本（5 个单竞品 + 2 个对比模式）进行评估，9 个自定义评估器覆盖多个维度。

| 评估器 | 类型 | baseline | optimized | 说明 |
|--------|------|----------|-----------|------|
| `sections_completeness` | 规则 | 1.00 | 1.00 | 报告章节完整度 |
| `source_coverage` | 规则 | 1.00 | 1.00 | 来源数量达标 |
| `report_length` | 规则 | 1.00 | 1.00 | 报告长度达标 |
| `data_density` | 规则 | - | 0.40 | 数据点密度 |
| `fact_consistency` | 规则 | 0.50 | **1.00** | 数字与原文一致性 |
| `comparison_coverage` | 规则 | 1.00 | 1.00 | 对比报告完整度 |
| `has_selection_advice` | 规则 | 0.40 | **0.55** | 选型建议覆盖度 |
| `honest_reporting` | 规则 | 1.00 | 1.00 | 数据缺失时诚实标注 |
| `report_quality` | LLM Judge | 0.57 | **0.67** | 完整性 / 数据 / 深度 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- LLM API Key
- Tavily API Key
- LangSmith API Key
- Qdrant Cloud 账号

### 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY、TAVILY_API_KEY、LANGSMITH_API_KEY等

python -m uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173。

---

## 项目结构

```
competitor-analysis-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── __init__.py
│   │   ├── llm.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── domains.py
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   └── workflow.py
│   │   ├── agents/
│   │   │   ├── memory_retriever.py
│   │   │   ├── planner.py
│   │   │   ├── collector.py
│   │   │   ├── analyzer.py
│   │   │   ├── quality_check.py
│   │   │   ├── switcher.py
│   │   │   ├── writer.py
│   │   │   ├── comparison_analyst.py
│   │   │   ├── comparison_writer.py
│   │   │   └── report_indexer.py
│   │   ├── memory/
│   │   │   ├── memory_manager.py    
│   │   │   └── text_splitter.py     
│   │   ├── services/
│   │   │   ├── search_service.py
│   │   │   └── report_service.py
│   │   ├── api/
│   │   │   ├── analysis.py
│   │   │   └── history.py
│   │   └── evaluation/
│   │       ├── dataset.py
│   │       ├── evaluators.py
│   │       └── run_eval.py
│   ├── data/
│   │   └── reports/                 
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue
│   │   │   ├── Analysis.vue
│   │   │   ├── Report.vue
│   │   │   └── History.vue
│   │   ├── services/api.ts
│   │   └── types/index.ts
│   └── package.json
├── .gitignore
└── README.md
```

---

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/analysis/start` | POST | 同步启动分析（阻塞直到完成） |
| `/api/analysis/stream` | POST | SSE 流式分析（实时推送进度） |
| `/api/analysis/{report_id}` | GET | 获取单份报告详情 |
| `/api/history` | GET | 列出历史报告 |
| `/api/history/{report_id}` | DELETE | 删除指定报告 |

---

