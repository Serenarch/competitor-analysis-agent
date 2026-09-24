"""质量检查节点：判断当前子任务的分析质量是否达标"""
from app.graph.state import CompetitorState


# 质量阈值
MIN_SUMMARY_LENGTH = 300   # 总结最少 300 字符
MIN_SOURCES = 2            # 最少 2 个来源
MAX_RETRY = 2              # 最多重试 2 次


def quality_check_node(state: CompetitorState) -> dict:
    """检查当前子任务的分析质量，并推进索引"""
    idx = state["current_task_index"]
    tasks = state["tasks"]

    if idx >= len(tasks):
        return {}

    task = tasks[idx]
    retry_count = state.get("retry_count", 0)

    # 找到当前任务的最新一条 summary
    current_summary = None
    for s in reversed(state["summaries"]):
        if s.task_id == task.id:
            current_summary = s
            break

    # 质量判断
    if current_summary is None:
        is_low_quality = True
        reason = "未生成总结"
    elif len(current_summary.summary) < MIN_SUMMARY_LENGTH:
        is_low_quality = True
        reason = f"总结过短 ({len(current_summary.summary)} < {MIN_SUMMARY_LENGTH})"
    elif len(current_summary.sources) < MIN_SOURCES:
        is_low_quality = True
        reason = f"来源过少 ({len(current_summary.sources)} < {MIN_SOURCES})"
    else:
        is_low_quality = False
        reason = "质量合格"

    print(f"[QualityCheck] 任务 {task.id}：{reason}")

    # 情况 1：质量不达标且还有重试机会 → 原地重试
    if is_low_quality and retry_count < MAX_RETRY:
        print(f"[QualityCheck] → 触发重试 (第 {retry_count + 1}/{MAX_RETRY} 次)")
        return {
            "retry_count": retry_count + 1,
        }

    # 情况 2：质量合格 或 达到重试上限 → 进入下一个任务
    if is_low_quality:
        print(f"[QualityCheck] → 达到重试上限，接受当前结果，进入下一任务")
    else:
        print(f"[QualityCheck] → 通过，进入下一任务")

    return {
        "current_task_index": idx + 1,
        "retry_count": 0,
    }