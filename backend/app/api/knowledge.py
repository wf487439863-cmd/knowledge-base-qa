"""知识库管理 API 路由（仅管理员可访问）"""
import os
import uuid
import asyncio
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.base import get_db, async_session
from app.models.user import User
from app.models.document import KnowledgeDocument
from app.dependencies import get_admin_user
from app.utils.response import success
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])


async def process_document_async(doc_id: int, file_path: str, file_type: str, original_name: str):
    """后台异步处理文档：加载 → 分割 → 嵌入 → 存入向量库"""
    from app.rag.loader import load_document
    from app.rag.splitter import split_documents
    from app.rag.retriever import add_documents_to_store

    print(f"[文档处理] 开始处理文档 #{doc_id}: {original_name}")
    async with async_session() as db:
        try:
            result = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                print(f"[文档处理] 文档 #{doc_id} 不存在")
                return
            doc.status = "processing"
            await db.commit()
            print(f"[文档处理] 状态更新为 processing")

            raw_docs = load_document(file_path, file_type)
            print(f"[文档处理] 文档加载完成，共 {len(raw_docs)} 页/段")

            chunks = split_documents(raw_docs)
            print(f"[文档处理] 分割完成，共 {len(chunks)} 个片段")

            chunk_count = await add_documents_to_store(chunks, doc_id, original_name)
            print(f"[文档处理] 向量库写入完成，共 {chunk_count} 条")

            doc.status = "completed"
            doc.chunk_count = chunk_count
            doc.char_count = sum(len(c.page_content) for c in chunks)
            await db.commit()
            print(f"[文档处理] 文档 #{doc_id} 处理完成")

        except Exception as e:
            traceback.print_exc()
            print(f"[文档处理] 文档 #{doc_id} 处理失败: {e}")
            async with async_session() as fail_db:
                result = await fail_db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
                )
                fail_doc = result.scalar_one_or_none()
                if fail_doc:
                    fail_doc.status = "failed"
                    fail_doc.error_message = str(e)[:500]
                    await fail_db.commit()


@router.get("/documents")
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status_filter: str = "",
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表（分页）"""
    query = select(KnowledgeDocument)
    count_query = select(func.count(KnowledgeDocument.id))

    if status_filter:
        query = query.where(KnowledgeDocument.status == status_filter)
        count_query = count_query.where(KnowledgeDocument.status == status_filter)

    query = query.order_by(KnowledgeDocument.created_at.desc())

    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    documents = result.scalars().all()

    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": d.id,
                "filename": d.filename,
                "original_name": d.original_name,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "chunk_count": d.chunk_count,
                "char_count": d.char_count,
                "status": d.status,
                "error_message": d.error_message,
                "created_at": d.created_at,
            }
            for d in documents
        ],
    })


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库"""
    # 校验文件类型
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {ext}，支持的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # 校验文件大小
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)",
        )

    # 保存文件
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    doc = KnowledgeDocument(
        filename=unique_name,
        original_name=file.filename or "unknown",
        file_type=ext,
        file_size=file_size,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 用 asyncio.create_task 启动后台处理（比 BackgroundTasks 更可靠）
    asyncio.create_task(
        process_document_async(doc.id, file_path, ext, file.filename or "unknown")
    )

    return success({
        "id": doc.id,
        "original_name": doc.original_name,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
    }, "文档上传成功，正在后台处理")


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（同时删除文件和向量数据）"""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 删除向量数据
    from app.rag.retriever import delete_documents_from_store
    await delete_documents_from_store(doc_id)

    # 删除物理文件
    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 删除数据库记录
    await db.delete(doc)
    await db.commit()

    return success(message="文档已删除")


@router.get("/stats")
async def knowledge_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库统计信息"""
    total_result = await db.execute(select(func.count(KnowledgeDocument.id)))
    total = total_result.scalar() or 0

    chunks_result = await db.execute(select(func.sum(KnowledgeDocument.chunk_count)))
    total_chunks = chunks_result.scalar() or 0

    chars_result = await db.execute(select(func.sum(KnowledgeDocument.char_count)))
    total_chars = chars_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.status == "completed")
    )
    completed = completed_result.scalar() or 0

    processing_result = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.status == "processing")
    )
    processing = processing_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.status == "failed")
    )
    failed = failed_result.scalar() or 0

    return success({
        "total_documents": total,
        "total_chunks": total_chunks,
        "total_chars": total_chars,
        "completed_documents": completed,
        "processing_documents": processing,
        "failed_documents": failed,
    })
