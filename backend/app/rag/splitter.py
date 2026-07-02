"""文本分割器"""
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import get_settings

settings = get_settings()


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """获取文本分割器实例"""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
        length_function=len,
    )


def split_documents(documents: List[Document]) -> List[Document]:
    """将文档列表分割为更小的片段"""
    splitter = get_text_splitter()
    chunks = splitter.split_documents(documents)

    # 为每个 chunk 保留原始来源信息
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        if "source" not in chunk.metadata:
            chunk.metadata["source"] = chunk.metadata.get("filename", "unknown")

    return chunks
