"""MemoryRetriever：从 Qdrant 检索历史报告片段"""
from app.graph.state import CompetitorState
from app.memory.memory_manager import vectorstore, memory_store
from qdrant_client.http import models


def memory_retriever_node(state: CompetitorState) -> dict:
    """检索历史记忆和相似报告片段"""
    competitor = state.get("competitor") or state["competitors"][0]
    user_id = state.get("user_id", "default_user")
    print(f"\n[MemoryRetriever] 正在为 {competitor} 检索历史记忆...")

    # --- A. 从 MemoryStore 读取用户偏好（不变） ---
    user_namespace = (user_id, "preferences")
    preferences = memory_store.search(user_namespace)
    pref_text = "\n".join([p.value.get("text", "") for p in preferences]) if preferences else ""

    # --- B. 从 Qdrant 检索相似的历史报告块 ---
    query = f"{competitor} 分析 {pref_text}"

    # 使用 metadata filter 限制检索范围，提高相关性
    search_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.competitor",
                match=models.MatchValue(value=competitor),
            )
        ]
    )

    # 先尝试带过滤的检索
    docs = vectorstore.similarity_search(
        query,
        k=5,  # 检索 5 个最相关的块
        filter=search_filter
    )

    # 如果带过滤没结果（比如首次分析），再尝试无过滤检索
    if not docs:
        docs = vectorstore.similarity_search(query, k=5)
        print(f"[MemoryRetriever] 无精确匹配，已回退到全局检索")

    # 将检索到的块按相似度排序，并限制总长度
    historical_context = "\n\n---\n\n".join([d.page_content for d in docs])
    print(f"[MemoryRetriever] 检索到 {len(docs)} 个历史片段，总长度 {len(historical_context)} 字符")

    return {
        "historical_context": historical_context,
        "user_preferences": pref_text,
    }