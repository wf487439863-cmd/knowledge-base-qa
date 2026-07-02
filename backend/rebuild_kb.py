"""知识库重建脚本 - 清空旧数据，从指定目录重新导入"""
import os, sys, asyncio

KB_DIR = r"D:\Desktop\知识库"

async def rebuild():
    from app.models.base import async_session, engine, Base
    from app.models.document import KnowledgeDocument
    from app.rag.loader import load_document, get_file_type
    from app.rag.splitter import split_documents
    from app.rag.retriever import add_documents_to_store, reset_vectorstore, get_vectorstore
    from sqlalchemy import select, delete

    # 1. 清空向量库
    print("[1/4] 清空旧向量库...")
    try:
        vs = get_vectorstore()
        all_ids = vs._collection.get()["ids"]
        if all_ids:
            vs._collection.delete(ids=all_ids)
    except Exception as e:
        print(f"  跳过向量库清理: {e}")
    reset_vectorstore()

    # 2. 清空文档表
    print("[2/4] 清空文档记录...")
    async with async_session() as db:
        await db.execute(delete(KnowledgeDocument))
        await db.commit()

    # 3. 扫描知识库目录
    print(f"[3/4] 扫描知识库: {KB_DIR}")
    files = []
    for f in os.listdir(KB_DIR):
        ext = get_file_type(f)
        if ext in ['.pdf', '.txt', '.md', '.csv', '.docx', '.html']:
            files.append((f, ext))

    if not files:
        print("  未找到支持的文件！支持的格式: pdf, txt, md, csv, docx, html")
        return

    # 4. 逐个导入
    print(f"[4/4] 导入 {len(files)} 个文档...")
    for fname, ext in files:
        file_path = os.path.join(KB_DIR, fname)
        print(f"  处理: {fname} ...", end=" ")

        try:
            # 创建数据库记录
            async with async_session() as db:
                doc = KnowledgeDocument(
                    filename=fname,
                    original_name=fname,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    status="processing",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)
                doc_id = doc.id

            # 加载 → 分割 → 嵌入
            raw_docs = load_document(file_path, ext)
            chunks = split_documents(raw_docs)
            chunk_count = await add_documents_to_store(chunks, doc_id, fname)

            # 更新状态
            async with async_session() as db:
                result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
                d = result.scalar_one_or_none()
                if d:
                    d.status = "completed"
                    d.chunk_count = chunk_count
                    d.char_count = sum(len(c.page_content) for c in chunks)
                    await db.commit()

            print(f"OK ({chunk_count} 片段)")

        except Exception as e:
            print(f"失败: {e}")

    print("\n知识库重建完成！")

if __name__ == "__main__":
    asyncio.run(rebuild())
