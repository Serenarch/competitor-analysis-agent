"""
LangGraph 全局状态定义

竞品分析流程的状态在节点之间传递。
- 输入字段：用户提交的竞品名称、行业、分析维度
- 中间字段：规划出的子任务、当前处理到第几个、采集的原始内容、分析总结
- 输出字段：最终报告
- 控制字段：重试次数、错误信息
- 记忆字段：历史上下文 + 用户偏好（RAG / Memory）
"""
from typing import TypedDict, Annotated, List, Optional, Dict
from operator import add
from pydantic import BaseModel, Field


# ============================================================
# 子结构（Pydantic，便于序列化和校验）
# ============================================================

class TodoItem(BaseModel):
    """规划出的子任务"""
    id: int = Field(..., description="任务编号，从 1 开始")
    title: str = Field(..., description="任务标题")
    intent: str = Field(..., description="研究意图")
    query: str = Field(..., description="搜索引擎查询语句")
    status: str = Field(default="pending", description="pending/running/completed/failed")


class SourceItem(BaseModel):
    """信息来源"""
    title: str = Field(..., description="网页标题")
    url: str = Field(..., description="网页链接")
    snippet: str = Field(..., description="内容摘要")


class TaskSummary(BaseModel):
    """单个子任务的分析总结"""
    competitor: str = Field(default="", description="属于哪个分析对象")
    task_id: int
    title: str
    summary: str = Field(..., description="Markdown 格式的分析总结")
    sources: List[SourceItem] = Field(default_factory=list)


# ============================================================
# LangGraph 全局状态
# ============================================================

class CompetitorState(TypedDict):
    """
    竞品分析全局状态

    注意 Annotated[List[X], add] 的用法：
    节点返回 {"summaries": [新summary]} 时，
    LangGraph 会自动把它追加到已有列表，而不是覆盖。
    """
    # ---------- 输入字段 ----------
    competitors: List[str]
    current_competitor: str
    comparison_mode: bool
    competitor: str
    industry: Optional[str]
    domain: str
    focus_areas: List[str]

    # ---------- 记忆字段 ----------
    user_id: str
    historical_context: Optional[str]
    user_preferences: Optional[str]

    # ---------- 规划阶段 ----------
    tasks: List[TodoItem]
    tasks_per_competitor: Dict[str, List[TodoItem]]

    # ---------- 执行阶段 ----------
    current_task_index: int
    raw_content: str
    raw_sources: List[dict]
    summaries: Annotated[List[TaskSummary], add]

    # ---------- 报告阶段 ----------
    report: Optional[str]
    report_type: str
    comparison_matrix: Optional[Dict]
    comparison_insights: Optional[str]

    # ---------- 控制字段 ----------
    retry_count: int
    error: Optional[str]
    status: str