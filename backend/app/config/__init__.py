"""配置包：加载环境变量、领域模板"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

class Settings:
    # LLM
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL")
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID")

    # LangSmith
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "competitor-analysis-agent")

    # 搜索
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # 服务
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()


if settings.LANGSMITH_TRACING:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT



from app.config.domains import get_domain_template, list_domains, DOMAIN_TEMPLATES

__all__ = [
    "settings",
    "Settings",
    "get_domain_template",
    "list_domains",
    "DOMAIN_TEMPLATES",
]
