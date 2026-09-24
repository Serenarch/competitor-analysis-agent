"""搜索服务：封装 Tavily API"""
import os
from typing import List, Dict, Any
from langchain_tavily import TavilySearch
from app.config import settings

if settings.TAVILY_API_KEY:
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY


class SearchService:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.tool = TavilySearch(
            max_results=max_results,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
        )

    def search(self, query: str) -> Dict[str, Any]:
        try:
            results = self.tool.invoke({"query": query})
        except Exception as e:
            print(f"[Search] 搜索失败: {e}")
            return {"answer": "", "sources": []}

        answer, sources = self._parse_results(results)

        # 去重
        seen = set()
        unique = []
        for s in sources:
            if s["url"] and s["url"] not in seen:
                seen.add(s["url"])
                unique.append(s)

        return {"answer": answer, "sources": unique[: self.max_results]}

    def _parse_results(self, results) -> tuple:
        answer = ""
        sources: List[Dict] = []

        if isinstance(results, str):
            return results, []

        if isinstance(results, list):
            for r in results:
                if not isinstance(r, dict):
                    continue
                if r.get("type") == "answer":
                    answer = r.get("answer") or r.get("content", "")
                    continue
                sources.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": (r.get("content") or r.get("raw_content") or "")[:500],
                })
        elif isinstance(results, dict):
            answer = results.get("answer", "")
            for r in results.get("results", []):
                sources.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": (r.get("content") or "")[:500],
                })

        return answer, sources


_search_service = None

def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service