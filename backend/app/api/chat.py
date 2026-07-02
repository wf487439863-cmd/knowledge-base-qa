"""知识库问答 API 路由 - 含 SSE 流式输出"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.base import get_db
from app.models.user import User
from app.models.session import ChatSession
from app.models.message import ChatMessage
from app.schemas.chat import SendMessage, SessionCreate
from app.dependencies import get_current_user
from app.rag.chain import rag_qa_stream
from app.utils.response import success
from app.utils.cache import get_cached_answer, set_cached_answer

router = APIRouter(prefix="/api/chat", tags=["知识库问答"])


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有会话列表"""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        # 统计消息数
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id)
        )
        msg_count = count_result.scalar() or 0
        items.append({
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "message_count": msg_count,
        })

    return success(items)


@router.post("/sessions")
async def create_session(
    data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    session = ChatSession(user_id=current_user.id, title=data.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return success({
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
    }, "会话创建成功")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    await db.delete(session)
    await db.commit()
    return success(message="会话已删除")


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话历史消息"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    return success({
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        },
        "messages": [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "sources": m.sources,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    })


@router.post("/sessions/{session_id}/send")
async def send_message(
    session_id: int,
    data: SendMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息并获取流式 RAG 回答 (SSE)"""
    # 验证会话所有权
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    # 保存用户消息
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)

    # 自动更新会话标题（首次问答）
    if session.title == "新对话":
        session.title = data.content[:30] + ("..." if len(data.content) > 30 else "")
    session.updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    await db.commit()
    await db.refresh(user_msg)

    # 获取对话历史（排除刚保存的用户消息）
    hist_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    all_messages = hist_result.scalars().all()
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in all_messages[:-1]
    ]

    # 检查缓存
    cached = await get_cached_answer(data.content)
    if cached:
        async def cached_response():
            yield f"data: {json.dumps({'type': 'token', 'content': cached['answer']}, ensure_ascii=False)}\n\n"
            if cached.get("sources"):
                yield f"data: {json.dumps({'type': 'sources', 'sources': cached['sources']}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        # 保存助手消息
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=cached["answer"],
            sources=cached.get("sources"),
        )
        db.add(assistant_msg)
        await db.commit()

        return StreamingResponse(
            cached_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 未命中缓存，启动 RAG 流式生成
    async def stream_response():
        full_answer = ""
        sources = None

        try:
            async for chunk in rag_qa_stream(data.content, chat_history):
                if chunk["type"] == "token":
                    full_answer += chunk["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']}, ensure_ascii=False)}\n\n"
                elif chunk["type"] == "sources":
                    sources = chunk["sources"]
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                elif chunk["type"] == "done":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        # 使用独立数据库会话保存助手消息
        from app.models.base import async_session as _async_session
        async with _async_session() as save_db:
            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=full_answer,
                sources=sources,
            )
            save_db.add(assistant_msg)
            await save_db.commit()

            # 更新会话时间
            result = await save_db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            sess = result.scalar_one_or_none()
            if sess:
                sess.updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                await save_db.commit()

        # 缓存问答结果
        if full_answer:
            cache_data = {"answer": full_answer}
            if sources:
                cache_data["sources"] = sources
            await set_cached_answer(data.content, cache_data)

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
