"""LangGraph 工作流：支持单竞品分析和多竞品对比 + 历史记忆"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import CompetitorState
from app.agents.memory_retriever import memory_retriever_node   # ★ 新增
from app.agents.planner import planner_node
from app.agents.collector import collector_node
from app.agents.analyzer import analyzer_node
from app.agents.quality_check import quality_check_node
from app.agents.switcher import switch_competitor_node
from app.agents.writer import writer_node
from app.agents.comparison_analyst import comparison_analyst_node
from app.agents.comparison_writer import comparison_writer_node
from app.agents.report_indexer import report_indexer_node        # ★ 新增


def route_after_analysis(state: CompetitorState) -> str:
    """
    分析完成后判断下一步：
    - 当前竞品还有子任务未完成 → collect（继续当前竞品）
    - 当前竞品完成，还有下一个竞品 → next_competitor
    - 全部完成，且是对比模式 → compare
    - 全部完成，且是单竞品模式 → write
    - 遇到错误 → end
    """
    if state.get("error"):
        print(f"[Router] 检测到错误：{state['error']}")
        return "end"

    current = state.get("current_competitor") or state.get("competitor", "")
    tasks_map = state.get("tasks_per_competitor", {})
    tasks = tasks_map.get(current) or state.get("tasks", [])
    task_idx = state.get("current_task_index", 0)

    # 当前竞品的子任务还没做完
    if task_idx < len(tasks):
        return "collect"

    # 所有竞品处理完成
    competitors = state.get("competitors", [])
    idx = competitors.index(current) if current in competitors else -1

    if idx < len(competitors) - 1:
        print(f"[Router] {current} 完成，还有 {len(competitors) - idx - 1} 个竞品未处理")
        return "next_competitor"

    print(f"[Router] 全部 {len(competitors)} 个竞品处理完成")

    # 判断是走对比模式还是单竞品模式
    if state.get("comparison_mode") and len(competitors) > 1:
        print(f"[Router] 进入对比分析阶段")
        return "compare"

    print(f"[Router] 进入报告生成阶段")
    return "write"


def build_graph():
    builder = StateGraph(CompetitorState)

    #记忆检索 + 报告索引
    builder.add_node("memory_retriever", memory_retriever_node)
    builder.add_node("report_indexer", report_indexer_node)

    # 原有节点
    builder.add_node("plan", planner_node)
    builder.add_node("collect", collector_node)
    builder.add_node("analyze", analyzer_node)
    builder.add_node("quality_check", quality_check_node)
    builder.add_node("switch_competitor", switch_competitor_node)
    builder.add_node("compare", comparison_analyst_node)
    builder.add_node("comparison_write", comparison_writer_node)
    builder.add_node("write", writer_node)

    # START 先走 memory_retriever，再进 plan
    builder.add_edge(START, "memory_retriever")
    builder.add_edge("memory_retriever", "plan")

    # 原有线性边
    builder.add_edge("plan", "collect")
    builder.add_edge("collect", "analyze")
    builder.add_edge("analyze", "quality_check")

    # 条件边：质量检查后判断
    builder.add_conditional_edges(
        "quality_check",
        route_after_analysis,
        {
            "collect": "collect",
            "next_competitor": "switch_competitor",
            "compare": "compare",
            "write": "write",
            "end": END,
        },
    )

    # 切换竞品后回到采集
    builder.add_edge("switch_competitor", "collect")


    builder.add_edge("compare", "comparison_write")
    builder.add_edge("comparison_write", "report_indexer")


    builder.add_edge("write", "report_indexer")


    builder.add_edge("report_indexer", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph