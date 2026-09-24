"""
API 请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# 从 graph.state 复用子结构，避免重复定义
from app.graph.state import TodoItem, SourceItem, TaskSummary


# ============================================================
# 请求
# ============================================================

class AnalysisRequest(BaseModel):
    """启动分析请求（支持单竞品和多竞品）"""
    # 单竞品兼容字段（新版本可选，老版本必填）
    competitor: Optional[str] = Field(
        default=None,
        description="单个分析对象名称（兼容旧接口）"
    )

    # 多竞品字段
    competitors: Optional[List[str]] = Field(
        default=None,
        description="多个分析对象名称，对比模式时使用"
    )

    industry: Optional[str] = Field(default=None, description="行业")
    domain: str = Field(
        default="software",
        description="领域：software / product / service"
    )
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="分析维度（不填则使用领域默认）"
    )

    @property
    def normalized_competitors(self) -> List[str]:
        """归一化：把 competitor / competitors 统一成列表"""
        if self.competitors:
            return [c.strip() for c in self.competitors if c.strip()]
        if self.competitor:
            return [self.competitor.strip()]
        return []

    @property
    def is_comparison_mode(self) -> bool:
        """是否为对比模式（超过 1 个对象）"""
        return len(self.normalized_competitors) > 1

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "competitor": "Notion",
                    "industry": "生产力工具",
                    "domain": "software"
                },
                {
                    "competitors": ["Notion", "Figma", "Linear"],
                    "industry": "生产力工具",
                    "domain": "software"
                }
            ]
        }
    }


# ============================================================
# 响应
# ============================================================

class AnalysisResponse(BaseModel):
    """启动分析响应"""
    report_id: str = Field(..., description="报告唯一 ID")
    competitor: str
    status: str = Field(..., description="running/completed/failed")
    message: str


class ReportDetail(BaseModel):
    """报告详情"""
    report_id: str
    competitor: str
    industry: Optional[str]
    domain: Optional[str] = None
    created_at: str
    report: str
    report_type: str = "single"

    # 中间产物
    tasks: List[TodoItem] = Field(default_factory=list)
    summaries: List[TaskSummary] = Field(default_factory=list)
    all_sources: List[SourceItem] = Field(default_factory=list)

    # 多竞品字段
    competitors: List[str] = Field(default_factory=list)
    comparison_mode: bool = False
    comparison_matrix: Optional[dict] = None
    comparison_insights: Optional[str] = None

    # 元数据
    duration_seconds: float = 0.0


class HistoryItem(BaseModel):
    """历史记录条目"""
    report_id: str
    competitor: str
    industry: Optional[str]
    created_at: str
    status: str


class HistoryResponse(BaseModel):
    """历史记录响应"""
    items: List[HistoryItem]
    total: int


# ============================================================
# SSE 事件
# ============================================================

class SSEEvent(BaseModel):
    """
    SSE 推送的事件

    type 取值：
    - status:    通用状态消息
    - tasks:     规划完成，推送子任务列表
    - progress:  进度更新（当前第 N 个）
    - summary:   某个子任务分析完成
    - report:    最终报告生成
    - error:     错误
    - done:      全部完成
    """
    type: str
    data: Optional[dict] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())