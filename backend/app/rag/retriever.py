"""向量检索器 - ChromaDB + MMR 多样性检索"""
from typing import List, Tuple
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from app.config import get_settings
from app.rag.loader import get_file_type

settings = get_settings()

# 全局向量库实例（懒加载）
_vectorstore: Chroma | None = None


def _get_embeddings():
    """获取 DashScope Embeddings 实例"""
    from langchain_community.embeddings import DashScopeEmbeddings
    return DashScopeEmbeddings(
        model=settings.EMBEDDING_MODEL,
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
    )


def get_vectorstore() -> Chroma:
    """获取或初始化 ChromaDB 向量存储"""
    global _vectorstore
    if _vectorstore is None:
        import os
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        _vectorstore = Chroma(
            collection_name=settings.CHROMA_COLLECTION,
            embedding_function=_get_embeddings(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
    return _vectorstore


def reset_vectorstore():
    """重置向量存储（用于重新加载）"""
    global _vectorstore
    _vectorstore = None


async def add_documents_to_store(
    documents: List[Document],
    doc_id: int,
    doc_name: str,
) -> int:
    """将文档片段添加到向量库，返回添加的片段数量"""
    vectorstore = get_vectorstore()

    # 为每个文档片段添加 ID 信息
    for doc in documents:
        doc.metadata["doc_id"] = doc_id
        doc.metadata["doc_name"] = doc_name

    ids = vectorstore.add_documents(documents)
    # 强制持久化 + 重置客户端，确保上传后立即可检索
    try:
        vectorstore.persist()
    except Exception:
        pass
    reset_vectorstore()
    return len(ids)


async def delete_documents_from_store(doc_id: int):
    """从向量库中删除指定文档的所有片段"""
    vectorstore = get_vectorstore()
    try:
        # ChromaDB 通过 metadata 过滤删除
        collection = vectorstore._collection
        results = collection.get(where={"doc_id": doc_id})
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception as e:
        print(f"删除向量数据失败: {e}")


async def similarity_search(
    query: str,
    top_k: int | None = None,
) -> List[Tuple[Document, float]]:
    """带 MMR 的混合检索"""
    if top_k is None:
        top_k = settings.MMR_TOP_K

    vectorstore = get_vectorstore()

    # 先用相似度搜索获取更多候选
    docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
        query, k=settings.RETRIEVAL_TOP_K
    )

    # 如果结果太少，直接返回
    if len(docs_with_scores) <= top_k:
        return docs_with_scores

    # 使用 MMR 做多样性检索
    try:
        mmr_docs = vectorstore.max_marginal_relevance_search(
            query,
            k=top_k,
            fetch_k=min(settings.MMR_FETCH_K, len(docs_with_scores)),
        )
        # 为 MMR 结果找对应分数
        scored = []
        for mmr_doc in mmr_docs:
            score = 0.0
            for doc, s in docs_with_scores:
                if doc.page_content == mmr_doc.page_content:
                    score = s
                    break
            scored.append((mmr_doc, score))
        return scored
    except Exception:
        return docs_with_scores[:top_k]
