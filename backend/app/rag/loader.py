"""文档加载器 - 支持多格式文档解析"""
import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    CSVLoader,
    UnstructuredHTMLLoader,
    Docx2txtLoader,
)


def load_document(file_path: str, file_type: str) -> List[Document]:
    """根据文件类型选择合适的 Loader 加载文档"""
    loaders = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
        ".csv": CSVLoader,
        ".html": UnstructuredHTMLLoader,
        ".docx": Docx2txtLoader,
    }

    loader_cls = loaders.get(file_type)
    if not loader_cls:
        raise ValueError(f"不支持的文件类型: {file_type}")

    loader = loader_cls(file_path, encoding="utf-8")
    return loader.load()


def get_file_type(filename: str) -> str:
    """获取文件扩展名（小写）"""
    return os.path.splitext(filename)[1].lower()
