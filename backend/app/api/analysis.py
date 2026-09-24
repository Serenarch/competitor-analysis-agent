"""分析接口：启动分析、SSE 流式、查询报告"""
import uuid
import json
import time
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import AnalysisRequest, AnalysisResponse, ReportDetail
from app.graph.workflow import get_graph
from app.services.report_service import get_report_service

router = APIRouter(prefix="/api/analysis", tags=["分析"])


def _make_initial_state(request: AnalysisRequest) -> dict:
    """构造初始状态"""
    competitors = request.normalized_competitors

    if not competitors:
        raise ValueError("至少需要一个分析对象")

    first_competitor = competitors[0]

    return {
        # 多竞品字段
        "competitors": competitors,
        "current_competitor": first_competitor,
        "comparison_mode": request.is_comparison_mode,
        "tasks_per_competitor": {},

        # 单竞品兼容字段（值等于第一个对象）
        "competitor": first_competitor,

        # 公共字段
        "industry": request.industry,
        "domain": request.domain,
        "focus_areas": request.focus_areas or [],

        # 执行状态
        "tasks": [],
        "current_task_index": 0,
        "raw_content": "",
        "raw_sources": [],
        "summaries": [],

        # 报告字段
        "report": None,
        "report_type": "comparison" if request.is_comparison_mode else "single",
        "comparison_matrix": None,
        "comparison_insights": None,

        # 控制字段
        "retry_count": 0,
        "error": None,
        "status": "pending",
    }


# ============================================================
# 1. 同步接口
# ============================================================

@router.post("/start", response_model=AnalysisResponse)
def start_analysis(request: AnalysisRequest):
    """同步启动分析，等待全部完成后返回"""
    competitors = request.normalized_competitors
    if not competitors:
        raise HTTPException(400, "至少需要一个分析对象")

    report_id = str(uuid.uuid4())[:8]
    graph = get_graph()
    config = {"configurable": {"thread_id": report_id}}

    print(f"\n[API] 启动分析：{competitors} (report_id={report_id})")
    start = time.time()

    try:
        result = graph.invoke(_make_initial_state(request), config=config)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"分析失败: {type(e).__name__}: {str(e)}")

    duration = time.time() - start
    result["duration_seconds"] = duration

    service = get_report_service()
    # 保存时用逗号分隔的 competitors 作为标题
    title = ", ".join(competitors)
    service.save(report_id, title, result)

    return AnalysisResponse(
        report_id=report_id,
        competitor=title,
        status=result.get("status", "unknown"),
        message=f"分析完成，耗时 {duration:.1f} 秒",
    )


# ============================================================
# 2. SSE 流式接口
# ============================================================

def _sse(event_type: str, data: dict = None, message: str = None) -> str:
    """构造一条 SSE 消息"""
    payload = {"type": event_type}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.post("/stream")
async def stream_analysis(request: AnalysisRequest):
    """SSE 流式分析：实时推送每个节点的进度"""
    # ---------- 新增：校验 ----------
    competitors = request.normalized_competitors
    if not competitors:
        raise HTTPException(400, "至少需要一个分析对象")

    title = ", ".join(competitors)

    report_id = str(uuid.uuid4())[:8]
    graph = get_graph()
    config = {"configurable": {"thread_id": report_id}}

    async def event_generator() -> AsyncGenerator[str, None]:
        start = time.time()
        final_state = None

        yield _sse("start", {
            "report_id": report_id,
            "competitor": title,
            "competitors": competitors,          # ← 新增：前端可以拿到完整列表
            "comparison_mode": request.is_comparison_mode,   # ← 新增
        })

        try:
            async for chunk in graph.astream(
                _make_initial_state(request),
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_output in chunk.items():
                    # 节点输出可能是 None（例如 quality_check 的默认分支）
                    if not isinstance(node_output, dict):
                        continue

                    if node_name == "plan":
                        tasks = node_output.get("tasks", [])
                        yield _sse("tasks", {
                            "tasks": [t.model_dump() for t in tasks]
                        })
                        yield _sse("status", message=f"已规划 {len(tasks)} 个子任务")

                    elif node_name == "collect":
                        yield _sse("status", message="正在采集资料...")

                    elif node_name == "analyze":
                        summaries = node_output.get("summaries", [])
                        if summaries:
                            s = summaries[-1]
                            yield _sse("summary", {
                                "task_id": s.task_id,
                                "title": s.title,
                                "summary": s.summary,
                                "source_count": len(s.sources),
                                "competitor": s.competitor,   # ← 新增
                            })

                    elif node_name == "quality_check":
                        yield _sse("status", message="质量检查完成")

                    elif node_name == "write":
                        report = node_output.get("report", "")
                        yield _sse("report", {"report": report})

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield _sse("error", message=f"{type(e).__name__}: {str(e)}")
            return

        # ---------- 持久化 ----------
        final_state = graph.get_state(config).values
        duration = time.time() - start

        # 附加耗时到状态
        final_state["duration_seconds"] = duration

        service = get_report_service()
        service.save(report_id, title, final_state)   # ← 用 title 保存

        yield _sse("done", {
            "report_id": report_id,
            "duration_seconds": round(duration, 1),
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 3. 查询接口
# ============================================================

@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(report_id: str):
    """根据 report_id 获取报告"""
    service = get_report_service()
    record = service.get(report_id)
    if not record:
        raise HTTPException(404, f"报告不存在: {report_id}")

    # 汇总所有来源
    all_sources = []
    for summary in record.get("summaries", []):
        for src in summary.get("sources", []):
            all_sources.append(src)

    return ReportDetail(
        report_id=record["report_id"],
        competitor=record["competitor"],
        industry=record.get("industry"),
        domain=record.get("domain"),
        created_at=record["created_at"],
        report=record["report"],
        report_type=record.get("report_type", "single"),
        tasks=record.get("tasks", []),
        summaries=record.get("summaries", []),
        all_sources=all_sources,
        competitors=record.get("competitors", []),
        comparison_mode=record.get("comparison_mode", False),
        comparison_matrix=record.get("comparison_matrix"),
        comparison_insights=record.get("comparison_insights"),
        duration_seconds=record.get("duration_seconds", 0.0),
    )