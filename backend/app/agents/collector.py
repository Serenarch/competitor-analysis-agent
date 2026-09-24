"""Collector Agent：采集当前竞品的当前子任务"""
from app.graph.state import CompetitorState
from app.services.search_service import get_search_service


def collector_node(state: CompetitorState) -> dict:
    """采集节点"""
    current = state.get("current_competitor") or state.get("competitor", "")
    tasks_map = state.get("tasks_per_competitor", {})
    tasks = tasks_map.get(current) or state.get("tasks", [])
    idx = state["current_task_index"]

    if idx >= len(tasks):
        return {"error": f"索引越界：{idx} >= {len(tasks)}"}

    task = tasks[idx]
    print(f"\n[Collector] 采集 {current} 任务 {task.id}/{len(tasks)}：{task.title}")
    print(f"[Collector] 查询：{task.query}")

    # 调用搜索服务
    service = get_search_service()
    result = service.search(task.query)

    answer = result.get("answer", "")
    sources = result.get("sources", [])

    # 组装 raw_content
    if answer:
        raw_content = answer
    else:
        raw_content = "\n\n".join([
            f"[{i+1}] {s['title']}\n{s['snippet']}"
            for i, s in enumerate(sources)
        ])

    print(f"[Collector] 采集完成：{len(sources)} 个来源")

    # 更新 task 状态为 completed
    updated_tasks = list(tasks)
    updated_tasks[idx] = task.model_copy(update={"status": "completed"})
    updated_map = dict(tasks_map)
    updated_map[current] = updated_tasks

    return {
        "raw_content": raw_content,
        "raw_sources": sources,
        "tasks_per_competitor": updated_map,
        "tasks": updated_tasks,   # 兼容字段
    }