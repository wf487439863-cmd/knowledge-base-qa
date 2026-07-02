"""FastAPI 应用主入口"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.models.base import init_db
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期事件"""
    # 启动时：初始化数据库
    print("[启动] 初始化数据库...")
    await init_db()
    print("[启动] 数据库初始化完成")

    # 确保必要目录存在
    from app.config import get_settings
    settings = get_settings()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    # 预热：提前初始化向量库和嵌入模型，避免首次请求等待
    try:
        from app.rag.retriever import get_vectorstore
        get_vectorstore()
        print("[启动] 向量库预热完成")
    except Exception as e:
        print(f"[启动] 向量库预热跳过: {e}")

    yield

    # 关闭时：清理资源
    print("[关闭] 应用正在关闭...")


app = FastAPI(
    title="RAG 企业级知识库问答系统",
    description="基于 LangChain + 阿里云百炼的电商知识库问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件（允许前端跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(knowledge_router)


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "version": "1.0.0"}


# 生产环境静态文件服务（前端构建产物）
# 开发时前端由 Vite 独立启动
import os as _os
_static_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "..", "frontend", "dist")
if _os.path.exists(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
    print(f"[启动] 静态文件服务已启用: {_static_dir}")
