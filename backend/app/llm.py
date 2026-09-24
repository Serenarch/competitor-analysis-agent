"""
LLM 工厂：统一管理 LLM 实例

好处：
1. 所有 Agent 用同一个配置，避免重复代码
2. 换模型只改一个地方
3. 自动接入 LangSmith 追踪
"""
from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """获取 LLM 实例

    Args:
        temperature: 0.0 用于规划和提取，0.3~0.7 用于创作
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL_ID,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=temperature,
    )