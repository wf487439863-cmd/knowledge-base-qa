"""应用配置管理 - 使用 Pydantic Settings 加载环境变量"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 使用绝对路径确保无论如何启动都能找到 .env
_ENV_FILE = str(Path(__file__).resolve().parent.parent / ".env")


class Settings(BaseSettings):
    # 阿里云百炼平台
    DASHSCOPE_API_KEY: str = ""  # 请在 .env 文件中配置
    LLM_MODEL: str = "qwen-plus"           # 问答生成模型
    EMBEDDING_MODEL: str = "text-embedding-v2"  # 文本向量化模型

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/knowledge_base.db"

    # JWT（默认值与 .env 保持一致，防止 .env 加载失败时密钥不匹配）
    JWT_SECRET_KEY: str = "kb-qa-prod-secret-change-me-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION: str = "ecommerce_knowledge"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False  # 开发阶段默认关闭

    # 文件上传
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".txt", ".md", ".csv", ".docx", ".html"]

    # RAG 参数
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 6
    MMR_FETCH_K: int = 10
    MMR_TOP_K: int = 4

    # 管理员预设
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "123456"

    # 语义缓存阈值
    CACHE_SIMILARITY_THRESHOLD: float = 0.95

    model_config = {"env_file": _ENV_FILE, "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
