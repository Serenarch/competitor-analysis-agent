import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langgraph.store.memory import InMemoryStore

# 1. 初始化嵌入模型
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 2. 初始化RAG向量库（持久化到本地）
CHROMA_PERSIST_DIR = "./data/chroma_db"
vectorstore = Chroma(
    collection_name="analysis_reports",
    embedding_function=embeddings,
    persist_directory=CHROMA_PERSIST_DIR,
)

# 3. 初始化LangGraph长期记忆存储
memory_store = InMemoryStore()