"""Planner Agent：为每个分析对象分别规划子任务"""
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.llm import get_llm
from app.graph.state import CompetitorState, TodoItem
from app.config.domains import get_domain_template


class PlannerOutput(BaseModel):
    tasks: List[TodoItem] = Field(
        ...,
        description="4~5 个分析子任务，按逻辑顺序排列",
        min_length=3,
        max_length=6,
    )



PLANNER_SYSTEM_TEMPLATE = """你是分析规划专家。你的任务是把一个{domain_display}的分析任务拆解为 4~5 个子任务。

{domain_hint}

【历史分析参考】
{historical_context}

每个子任务需要覆盖一个独立的分析维度。要求：
1. 每个子任务的 query 用英文
2. query 要具体，包含分析对象名称和维度关键词
3. title 和 intent 用中文，简洁明了
4. 如果历史分析中提到了重要的分析角度，可以纳入本次规划
"""

PLANNER_USER = """请为以下分析任务制定规划：

分析对象：{competitor}
所属行业：{industry}
分析维度：{focus_areas}

请拆解为 4~5 个子任务。"""



def _plan_one(
    competitor: str,
    industry: str,
    focus_areas: List[str],
    domain: str,
    historical_context: str = "",
) -> List[TodoItem]:
    """为单个对象规划子任务"""
    template = get_domain_template(domain)

    prompt = ChatPromptTemplate.from_messages([
        ("system", PLANNER_SYSTEM_TEMPLATE.format(
            domain_display=template["display_name"],
            domain_hint=template["planner_hint"],
            historical_context=historical_context or "（本次为该对象的首次分析，无历史记录）",
        )),
        ("user", PLANNER_USER),
    ])

    llm = get_llm(temperature=0.0)
    chain = prompt | llm.with_structured_output(PlannerOutput)

    result: PlannerOutput = chain.invoke({
        "competitor": competitor,
        "industry": industry,
        "focus_areas": "、".join(focus_areas),
    })

    tasks = []
    for i, task in enumerate(result.tasks, start=1):
        tasks.append(TodoItem(
            id=i,
            title=task.title,
            intent=task.intent,
            query=task.query,
            status="pending",
        ))
    return tasks


def planner_node(state: CompetitorState) -> dict:
    """规划节点：为每个分析对象分别规划"""
    competitors = state.get("competitors") or [state["competitor"]]
    domain = state.get("domain", "software")
    template = get_domain_template(domain)
    focus_areas = state.get("focus_areas") or template["focus_areas"]
    industry = state.get("industry") or "通用"

    historical_context = state.get("historical_context", "") or ""

    print(f"\n[Planner] 开始规划，共 {len(competitors)} 个对象（领域：{template['display_name']}）")
    if historical_context:
        print(f"[Planner] 已注入历史上下文（{len(historical_context)} 字符）")

    tasks_per_competitor: Dict[str, List[TodoItem]] = {}
    for comp in competitors:
        print(f"[Planner] 为 {comp} 规划子任务...")

        tasks = _plan_one(comp, industry, focus_areas, domain, historical_context)
        tasks_per_competitor[comp] = tasks
        print(f"[Planner]   {comp}: {len(tasks)} 个子任务")

    first = competitors[0]

    return {
        "tasks_per_competitor": tasks_per_competitor,
        "current_competitor": first,
        "competitor": first,
        "tasks": tasks_per_competitor[first],
        "current_task_index": 0,
        "status": "running",
    }