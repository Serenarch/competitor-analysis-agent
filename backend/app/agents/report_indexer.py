import uuid
from langchain_core.documents import Document
from app.graph.state import CompetitorState
from app.memory.memory_manager import vectorstore, memory_store


def report_indexer_node(state: CompetitorState) -> dict:
    """将新报告索引到RAG，并更新用户长期记忆"""
    report = state.get("report", "")
    competitor = state.get("competitor") or state["competitors"][0]
    user_id = state.get("user_id", "default_user")

    if not report:
        return {}

    # --- A. 将报告存入RAG向量库 ---
    # 将整个报告作为一个Document存入
    doc = Document(
        page_content=report,
        metadata={"competitor": competitor, "report_id": state.get("report_id", "")}
    )
    # 生成唯一ID
    doc_id = str(uuid.uuid4())
    vectorstore.add_documents([doc], ids=[doc_id])
    print(f"[ReportIndexer] 报告已索引到RAG: {doc_id}")

    # --- B. 更新用户长期记忆 ---
    # 从报告中提取用户偏好或事实，存入MemoryStore
    user_namespace = (user_id, "preferences")
    memory_id = str(uuid.uuid4())
    memory_store.put(
        user_namespace,
        memory_id,
        {"text": f"分析过 {competitor}，报告摘要：{report[:200]}..."}
    )
    print(f"[ReportIndexer] 用户记忆已更新: {memory_id}")

    return {}