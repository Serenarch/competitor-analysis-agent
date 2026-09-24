"""ComparisonAnalyst 节点：把多个竞品的同类总结对齐，生成对比矩阵"""
import json
from typing import Dict, List, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.graph.state import CompetitorState
from app.config.domains import get_domain_template


# ============================================================
# 结构化输出模型
# ============================================================

class ComparisonMatrix(BaseModel):
    """对比矩阵 + 洞察"""
    dimensions: Dict[str, Dict[str, str]] = Field(
        ...,
        description=(
            "对比矩阵。格式：{维度名: {竞品名: 该竞品在此维度的总结}}。"
            "维度名用报告章节，如 '产品定位'、'核心功能'、'定价策略'"
        ),
    )
    key_insights: str = Field(
        ...,
        description="对比洞察，200-500 字，指出关键差异和各竞品的优劣势",
        min_length=100,
    )


# ============================================================
# 提示词
# ============================================================

COMPARISON_PROMPT = """你是竞品对比分析专家。以下是 {n} 个分析对象的总结。

{all_summaries}

请完成两个任务：

【任务 1：生成对比矩阵】
将各对象的分析结果按维度对齐，形成对比矩阵。

**严格的数字保留规则（非常重要）：**
- 所有数字必须**原样保留**，禁止修改、四舍五入、概括
- 例如：原文"$16/月"必须写"$16/月"，不能写成"约$16"或"$20"
- 例如：原文"1300 万用户"必须写"1300 万用户"，不能改成"约 1000 万"
- 例如：原文"41.78% 市场份额"必须完整保留
- 如果原文提到多个数字（如四个套餐价格），全部保留

**压缩规则：**
- 每个维度下，每个对象的总结压缩到 80 字以内
- 突出差异，不复述所有信息
- 如果某个对象在某维度没有数据，写"未找到"

【任务 2：写对比洞察】
200-500 字，回答：
- 各对象的核心差异是什么？
- 各自的优劣势？
- 适合什么场景？

请严格按 JSON 格式返回：
{{
  "dimensions": {{
    "维度名1": {{"对象A": "总结A", "对象B": "总结B"}},
    "维度名2": {{"对象A": "总结A", "对象B": "总结B"}}
  }},
  "key_insights": "对比洞察文本"
}}
"""


# ============================================================
# 辅助函数
# ============================================================

def _dedupe_summaries(summaries: list) -> list:
    """按 (competitor, task_id) 去重，保留最新"""
    latest = {}
    for s in summaries:
        key = (getattr(s, "competitor", "") or "", s.task_id)
        latest[key] = s
    return sorted(latest.values(), key=lambda x: (x.competitor, x.task_id))


def _format_summaries(unique_summaries: list, competitors: list) -> str:
    """按竞品分组格式化 summaries"""
    grouped = {}
    for s in unique_summaries:
        grouped.setdefault(s.competitor, []).append(s)

    parts = []
    for comp in competitors:
        items = grouped.get(comp, [])
        if not items:
            continue
        parts.append(f"## {comp}")
        for s in items:
            parts.append(f"### {s.title}\n{s.summary}")
        parts.append("")
    return "\n\n".join(parts)


# ============================================================
# ComparisonAnalyst 节点
# ============================================================

def comparison_analyst_node(state: CompetitorState) -> dict:
    """对比分析节点：生成对比矩阵 + 洞察"""
    competitors = state.get("competitors") or []
    if len(competitors) < 2:
        return {"error": "对比模式需要至少 2 个分析对象"}

    domain = state.get("domain", "software")
    template = get_domain_template(domain)

    print(f"\n[ComparisonAnalyst] 开始对比分析：{competitors}")

    # 1. 去重 + 格式化
    unique = _dedupe_summaries(state.get("summaries", []))
    print(f"[ComparisonAnalyst] 去重后 {len(unique)} 条总结")

    all_text = _format_summaries(unique, competitors)

    # 2. 调 LLM
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"你是一位资深分析师，擅长从{template['display_name']}角度做多对象对比。"),
        ("user", COMPARISON_PROMPT),
    ])

    llm = get_llm(temperature=0.0)
    chain = prompt | llm.with_structured_output(ComparisonMatrix)

    result: ComparisonMatrix = chain.invoke({
        "n": len(competitors),
        "all_summaries": all_text[:15000],
    })

    print(f"[ComparisonAnalyst] 完成，维度数：{len(result.dimensions)}")
    print(f"[ComparisonAnalyst] 洞察长度：{len(result.key_insights)} 字符")

    return {
        "comparison_matrix": result.dimensions,
        "comparison_insights": result.key_insights,
    }
