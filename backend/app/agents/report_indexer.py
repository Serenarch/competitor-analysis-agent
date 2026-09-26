"""ReportIndexer：分块索引报告，并更新用户记忆"""
import uuid
from langchain_core.documents import Document
from app.graph.state import CompetitorState
from app.memory.memory_manager import vectorstore, memory_store
from app.memory.text_splitter import split_report  # 导入分块器


def report_indexer_node(state: CompetitorState) -> dict:
    """将报告分块索引到 Qdrant，并更新用户长期记忆"""
    report = state.get("report", "")
    competitor = state.get("competitor") or state["competitors"][0]
    user_id = state.get("user_id", "default_user")

    if not report:
        return {}

    # 1. 按 Markdown 标题分块
    chunks = split_report(report)
    print(f"[ReportIndexer] 报告已切分为 {len(chunks)} 个块")

    # 2. 为每个块添加元数据
    docs_to_add = []
    for i, chunk in enumerate(chunks):
        # 构建带章节信息的元数据
        section = chunk.metadata.get("h3") or chunk.metadata.get("h2") or chunk.metadata.get("h1") or "正文"
        doc = Document(
            page_content=chunk.page_content,
            metadata={
                "competitor": competitor,
                "section": section,
                "chunk_index": i,
                "report_id": state.get("report_id", ""),
            }
        )
        docs_to_add.append(doc)

    # 3. 批量写入 Qdrant
    ids = [str(uuid.uuid4()) for _ in docs_to_add]
    vectorstore.add_documents(documents=docs_to_add, ids=ids)
    print(f"[ReportIndexer] 已将 {len(ids)} 个块索引到 Qdrant")

    # 4. 更新用户长期记忆（逻辑不变）
    user_namespace = (user_id, "preferences")
    memory_id = str(uuid.uuid4())
    memory_store.put(
        user_namespace,
        memory_id,
        {"text": f"分析过 {competitor}，报告摘要：{report[:200]}..."}
    )
    print(f"[ReportIndexer] 用户记忆已更新: {memory_id}")

    return {}