from app.graph.state import CompetitorState
from app.memory.memory_manager import vectorstore, memory_store


def memory_retriever_node(state: CompetitorState) -> dict:
    """检索历史记忆和相似报告，作为分析的起点上下文"""
    competitor = state.get("competitor") or state["competitors"][0]
    user_id = state.get("user_id", "default_user")
    print(f"\n[MemoryRetriever] 正在为 {competitor} 检索历史记忆...")

    # --- A. 从MemoryStore读取用户偏好 ---
    user_namespace = (user_id, "preferences")
    preferences = memory_store.search(user_namespace)
    pref_text = "\n".join([p.value.get("text", "") for p in preferences]) if preferences else ""

    # --- B. 从Chroma检索相似的历史报告片段 ---
    query = f"{competitor} 分析 {pref_text}"
    docs = vectorstore.similarity_search(query, k=3)
    historical_context = "\n\n".join([d.page_content for d in docs])
    # --- C. 检索保存记录 ---
    docs = vectorstore.similarity_search(query, k=3)
    print(f"[MemoryRetriever] 检索到 {len(docs)} 条历史片段")
    historical_context = "\n\n".join([d.page_content for d in docs])
    print(f"[MemoryRetriever] 上下文长度：{len(historical_context)} 字符")
    return {
        "historical_context": historical_context,
        "user_preferences": pref_text,
    }