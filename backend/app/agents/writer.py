"""Writer Agent：整合所有子任务总结，生成最终报告（支持多领域 + 多竞品）"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.graph.state import CompetitorState
from app.config.domains import get_domain_template


# ============================================================
# 结构化输出模型
# ============================================================

class WriterOutput(BaseModel):
    report: str = Field(
        ...,
        description="Markdown 格式的完整分析报告",
        min_length=200,
    )


# ============================================================
# 提示词模板
# ============================================================

WRITER_SYSTEM_TEMPLATE = """你是资深分析师。请基于子任务分析结果，生成一份专业的{domain_display}分析报告。

报告结构（必须包含以下所有章节，缺一不可）：
{sections_list}

【数据支撑要求 - 非常重要】
1. 每个章节必须包含至少 2 个具体数字（金额、百分比、用户数、评分、日期等）
2. 定价/价格章节必须列出所有套餐/规格的具体价格
3. 竞争格局章节必须包含市场份额、用户规模等对比数据
4. 用户评价/口碑章节必须引用具体评分（如 G2 4.5 分、Capterra 4.3 分）
5. 禁止写"用户很多"、"价格较高"、"市场领先"这类模糊表述，必须量化
6. 如果子任务总结中提到了具体数据，必须原样保留到最终报告
7. 数据缺失时明确写"未找到"或"未公开"，不要编造

【分析深度要求】
8. 每个章节末尾必须有一段"洞察"：不仅说明是什么，还要分析为什么、意味着什么
9. SWOT 分析中每一条都要有具体的论据支撑
10. 结论与建议必须区分优先级，并说明每条建议的依据
11. 避免简单罗列信息，要有分析性的语言

【格式要求】
- 使用 Markdown 格式
- 章节标题使用二级标题（##）
- 表格使用 Markdown 表格语法
- 基于给定信息，不要编造
"""

WRITER_USER = """分析对象：{competitor}
所属行业：{industry}
分析领域：{domain_display}

以下是各子任务的分析结果：

{summaries}

请整合生成完整的分析报告。"""


# ============================================================
# 辅助函数
# ============================================================

def _dedupe_summaries(summaries: list) -> list:
    """
    按 (competitor, task_id) 去重，保留每个 key 的最新一条。

    为什么用 (competitor, task_id) 而不是 task_id？
    - 多竞品场景下，每个竞品都有自己的 task_id=1, 2, 3...
    - 如果只按 task_id 去重，Notion 的 task 1 会被 Figma 的 task 1 覆盖
    """
    latest_by_key = {}
    for s in summaries:
        key = (getattr(s, "competitor", "") or "", s.task_id)
        latest_by_key[key] = s
    # 按竞品顺序 + task_id 排序
    return sorted(latest_by_key.values(), key=lambda x: (x.competitor, x.task_id))


def _build_summaries_text(unique_summaries: list, competitors: list) -> str:
    """
    拼装 summaries 文本。

    - 多竞品：按竞品分组，加一级标题
    - 单竞品：平铺展示
    """
    if len(competitors) > 1:
        # 多竞品：按竞品分组
        grouped = {}
        for s in unique_summaries:
            grouped.setdefault(s.competitor, []).append(s)

        parts = []
        for comp in competitors:
            items = grouped.get(comp, [])
            if not items:
                continue
            parts.append(f"# {comp}")
            for s in items:
                parts.append(f"## {s.title}\n\n{s.summary}")
            parts.append("")  # 空行分隔
        return "\n\n".join(parts)
    else:
        # 单竞品：平铺
        return "\n\n".join([
            f"### 子任务 {s.task_id}：{s.title}\n\n{s.summary}"
            for s in unique_summaries
        ])


# ============================================================
# Writer 节点
# ============================================================

def writer_node(state: CompetitorState) -> dict:
    """报告节点：生成最终报告"""
    domain = state.get("domain", "software")
    template = get_domain_template(domain)

    # 兼容单竞品/多竞品
    competitors = state.get("competitors") or [state.get("competitor", "")]
    competitors = [c for c in competitors if c]

    title = ", ".join(competitors) if len(competitors) > 1 else competitors[0]

    print(f"\n[Writer] 开始生成报告：{title}（领域：{template['display_name']}）")

    if not state.get("summaries"):
        return {
            "report": "# 分析失败\n\n未能采集到任何信息。",
            "status": "failed",
            "error": "没有可用的子任务总结",
        }

    # ------------------------------------------------------------
    # 1. 按 (competitor, task_id) 去重
    # ------------------------------------------------------------
    unique_summaries = _dedupe_summaries(state["summaries"])
    print(f"[Writer] 去重后 {len(unique_summaries)} 条有效总结")

    # ------------------------------------------------------------
    # 2. 拼装 summaries 文本
    # ------------------------------------------------------------
    summaries_text = _build_summaries_text(unique_summaries, competitors)

    # ------------------------------------------------------------
    # 3. 根据领域动态生成章节列表
    # ------------------------------------------------------------
    sections_list = "\n".join([
        f"{i+1}. {section}"
        for i, section in enumerate(template["report_sections"])
    ])

    # ------------------------------------------------------------
    # 4. 构建提示词
    # ------------------------------------------------------------
    system_prompt = WRITER_SYSTEM_TEMPLATE.format(
        domain_display=template["display_name"],
        sections_list=sections_list,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", WRITER_USER),
    ])

    # ------------------------------------------------------------
    # 5. 调用 LLM
    # ------------------------------------------------------------
    llm = get_llm(temperature=0.3)
    chain = prompt | llm.with_structured_output(WriterOutput)

    result: WriterOutput = chain.invoke({
        "competitor": title,
        "industry": state.get("industry") or "通用",
        "domain_display": template["display_name"],
        "summaries": summaries_text[:15000],
    })

    print(f"[Writer] 报告生成完成，长度：{len(result.report)} 字符")

    return {
        "report": result.report,
        "report_type": "single",
        "status": "completed",
    }