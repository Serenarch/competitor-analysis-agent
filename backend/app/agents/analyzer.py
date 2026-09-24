"""Analyzer Agent：提炼当前子任务的关键信息"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.graph.state import CompetitorState, TaskSummary, SourceItem


class AnalyzerOutput(BaseModel):
    summary: str = Field(
        ...,
        description="Markdown 格式的分析总结，包含核心发现、关键数据、关键结论",
        min_length=20,
    )



ANALYZER_SYSTEM_TEMPLATE = """你是竞品分析专家。请基于给定的搜索结果，提炼该子任务的关键信息。

【历史分析参考】
{historical_context}

输出要求：
1. 使用 Markdown 格式
2. 结构：核心发现（3-5 条）、关键数据、关键结论
3. 只基于给定内容，不要编造

【数据提取要求 - 非常重要】
4. "关键数据"部分必须尽可能完整，逐条列出搜索结果中出现的所有量化信息：
   - 用户量（MAU/DAU/注册用户数）
   - 财务数据（营收、估值、融资额、增长率）
   - 价格（套餐金额、单价、折扣）
   - 评分（G2/Capterra 分数、评论数）
   - 市场份额、百分比、排名
   - 时间节点（成立年份、产品发布日）
5. 每条数据必须带具体数字，禁止写"用户量很大"、"价格适中"这种模糊表述
6. 如果搜索结果中确实没有某项数据，明确写"未找到"
7. 如果历史分析中已有相关结论，可以在本次分析中做对比或补充
"""

ANALYZER_USER = """竞品：{competitor}

当前子任务：{task_title}
任务意图：{task_intent}

搜索结果：
{raw_content}

请提炼该子任务的关键信息。"""


# ============================================================
# Prompt 污染检测
# ============================================================

POLLUTION_MARKERS = [
    "你是一位竞品分析专家",
    "输出要求：",
    "数据提取要求",
    "关键数据\"部分必须",
    "请基于给定内容",
    "请基于给定的搜索结果",
    "禁止写",
    "明确写\"未找到\"",
    "结构：核心发现",
    "只基于给定内容",
]


def _is_polluted(text: str) -> bool:
    """检测 summary 是否包含 prompt 污染"""
    if not text or len(text) < 30:
        return False
    hit_count = sum(1 for marker in POLLUTION_MARKERS if marker in text)
    return hit_count >= 2


def _build_fallback_summary(raw_content: str) -> str:
    """当 LLM 输出异常时，用原始搜索结果构造兜底 summary"""
    excerpt = raw_content[:800] if raw_content else "无可用信息"

    return (
        f"## 核心发现\n\n"
        f"（LLM 输出格式异常，以下为原始搜索结果摘录，需人工复核）\n\n"
        f"## 关键数据\n\n"
        f"未找到（原始结果未包含结构化数据）\n\n"
        f"## 关键结论\n\n"
        f"{excerpt}"
    )


# ============================================================
# Analyzer 节点
# ============================================================

def analyzer_node(state: CompetitorState) -> dict:
    """分析节点：提炼当前子任务的总结（不推进索引）"""
    current = state.get("current_competitor") or state.get("competitor", "")
    tasks_map = state.get("tasks_per_competitor", {})
    tasks = tasks_map.get(current) or state.get("tasks", [])
    idx = state["current_task_index"]

    historical_context = state.get("historical_context", "") or ""

    if idx >= len(tasks):
        return {"error": f"索引越界：{idx}"}

    task = tasks[idx]
    raw_content = state.get("raw_content", "")
    raw_sources = state.get("raw_sources", [])

    print(f"\n[Analyzer] 分析 {current} 任务 {task.id}/{len(tasks)}：{task.title}")

    if not raw_content:
        summary = TaskSummary(
            competitor=current,
            task_id=task.id,
            title=task.title,
            summary="未采集到相关信息，无法进行分析。",
            sources=[],
        )
        return {"summaries": [summary]}


    prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYZER_SYSTEM_TEMPLATE.format(
            historical_context=historical_context or "（无历史分析记录）",
        )),
        ("user", ANALYZER_USER),
    ])

    llm = get_llm(temperature=0.0)
    chain = prompt | llm.with_structured_output(AnalyzerOutput)

    summary_text = ""
    try:
        result: AnalyzerOutput = chain.invoke({
            "competitor": current,
            "task_title": task.title,
            "task_intent": task.intent,
            "raw_content": raw_content[:8000],
        })
        summary_text = result.summary
    except Exception as e:
        print(f"[Analyzer] ⚠️ LLM 调用异常：{type(e).__name__}: {e}")
        summary_text = _build_fallback_summary(raw_content)

    if _is_polluted(summary_text):
        print(f"[Analyzer] ⚠️ 检测到 prompt 污染，使用原始内容兜底")
        print(f"[Analyzer]    污染内容前 100 字：{summary_text[:100]}")
        summary_text = _build_fallback_summary(raw_content)

    if len(summary_text) < 20:
        print(f"[Analyzer] ⚠️ summary 太短（{len(summary_text)} 字符），使用原始内容兜底")
        summary_text = _build_fallback_summary(raw_content)

    sources = [SourceItem(**s) for s in raw_sources if s.get("url")]
    summary = TaskSummary(
        competitor=current,
        task_id=task.id,
        title=task.title,
        summary=summary_text,
        sources=sources,
    )

    print(f"[Analyzer] 分析完成，总结长度: {len(summary_text)} 字符")

    return {"summaries": [summary]}