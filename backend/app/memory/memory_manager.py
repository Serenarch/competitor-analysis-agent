"""统一管理 Qdrant 向量库和 LangGraph 长期记忆"""
import os

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.store.memory import InMemoryStore


# ============================================================
# 1. 嵌入模型（全局单例，存和查共用）
# ============================================================
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)


# ============================================================
# 2. Qdrant Cloud 客户端
# ============================================================
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError(
        "请在 backend/.env 中配置 QDRANT_URL 和 QDRANT_API_KEY。\n"
        "示例：\n"
        "  QDRANT_URL=https://xxx.region.aws.cloud.qdrant.io:6333\n"
        "  QDRANT_API_KEY=your_api_key"
    )

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=True,
    timeout=30,
)

COLLECTION_NAME = "analysis_reports"


# ============================================================
# 3. 创建集合 + Payload 索引
# ============================================================
if not client.collection_exists(collection_name=COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=512, distance=Distance.COSINE),
    )
    print(f"[Qdrant] 已创建集合：{COLLECTION_NAME}")


# 确保 metadata.competitor 索引存在（用于按竞品过滤）
try:
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="metadata.competitor",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    print("[Qdrant] metadata.competitor 索引就绪")
except Exception as e:
    # 如果索引已存在，Qdrant 可能抛异常，忽略
    print(f"[Qdrant] metadata.competitor 索引已存在或创建失败：{e}")


# ============================================================
# 4. 向量存储
# ============================================================
vectorstore = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
    distance=Distance.COSINE,
)


# ============================================================
# 5. LangGraph 长期记忆（内存态）
# ============================================================
memory_store = InMemoryStore()