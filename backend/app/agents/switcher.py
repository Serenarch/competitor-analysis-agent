"""切换竞品节点：一个竞品处理完后，切换到下一个"""
from app.graph.state import CompetitorState


def switch_competitor_node(state: CompetitorState) -> dict:
    """切换到下一个竞品"""
    competitors = state.get("competitors", [])
    current = state.get("current_competitor") or state.get("competitor", "")

    if current not in competitors:
        return {"error": f"当前竞品 {current} 不在列表中"}

    idx = competitors.index(current)
    if idx >= len(competitors) - 1:
        return {"error": "已经是最后一个竞品，不应进入 switch 节点"}

    next_comp = competitors[idx + 1]
    tasks_map = state.get("tasks_per_competitor", {})
    next_tasks = tasks_map.get(next_comp, [])

    print(f"\n[Router] 切换到下一个竞品：{next_comp}（{len(next_tasks)} 个子任务）")

    return {
        "current_competitor": next_comp,
        "competitor": next_comp,
        "tasks": next_tasks,
        "current_task_index": 0,
        "raw_content": "",
        "raw_sources": [],
        "retry_count": 0,
    }