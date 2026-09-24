"""报告持久化服务：保存和读取分析报告"""
import json
import os
from datetime import datetime
from typing import Optional, List
from app.config import settings

REPORTS_DIR = os.path.join("data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class ReportService:
    """管理分析报告的存储"""

    def save(self, report_id: str, competitor: str, result: dict) -> dict:
        """保存报告"""
        record = {
            "report_id": report_id,
            "competitor": competitor,
            "industry": result.get("industry"),
            "domain": result.get("domain"),
            "created_at": datetime.now().isoformat(),
            "status": result.get("status", "unknown"),

            # 报告内容
            "report": result.get("report", ""),
            "report_type": result.get("report_type", "single"),

            # 中间产物
            "tasks": [t.model_dump() if hasattr(t, "model_dump") else t
                      for t in result.get("tasks", [])],
            "summaries": [s.model_dump() if hasattr(s, "model_dump") else s
                          for s in result.get("summaries", [])],
            "tasks_per_competitor": {
                k: [t.model_dump() if hasattr(t, "model_dump") else t for t in v]
                for k, v in result.get("tasks_per_competitor", {}).items()
            },  # ← 新增

            # 多竞品字段
            "competitors": result.get("competitors", []),
            "comparison_mode": result.get("comparison_mode", False),
            "comparison_matrix": result.get("comparison_matrix"),
            "comparison_insights": result.get("comparison_insights"),

            # 元数据
            "duration_seconds": result.get("duration_seconds", 0.0),
        }
        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return record

    def get(self, report_id: str) -> Optional[dict]:
        """读取单个报告"""
        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_all(self, limit: int = 20) -> List[dict]:
        """列出所有报告（按时间倒序）"""
        if not os.path.exists(REPORTS_DIR):
            return []
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")]
        records = []
        for fname in files:
            try:
                with open(os.path.join(REPORTS_DIR, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    records.append({
                        "report_id": data.get("report_id"),
                        "competitor": data.get("competitor"),
                        "industry": data.get("industry"),
                        "created_at": data.get("created_at"),
                        "status": data.get("status"),
                    })
            except Exception:
                continue
        records.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return records[:limit]

    def delete(self, report_id: str) -> bool:
        """删除报告"""
        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False


_report_service = None

def get_report_service() -> ReportService:
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service