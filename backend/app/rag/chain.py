"""LangChain RAG Chain - 高性能精简版"""
from typing import AsyncIterator, List, Dict, Any
from langchain_community.chat_models.tongyi import ChatTongyi
from app.config import get_settings
from app.rag.retriever import similarity_search
from app.rag.prompt import SYSTEM_PROMPT

settings = get_settings()


def _get_llm(streaming: bool = True):
    """获取 ChatTongyi，qwen-turbo 速度快 2-3 倍"""
    return ChatTongyi(
        model="qwen-plus",  # turbo→plus 提升回答质量
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
        streaming=streaming,
        temperature=0.5,  # 提高温度，回答更自然
        top_p=0.8,
        max_tokens=1024,
    )


def _format_chat_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "无历史对话"
    return "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
        for m in history[-4:]  # 只保留最近 4 轮
    )


def _format_context(docs_with_scores: List[tuple]) -> tuple[str, List[Dict]]:
    """将检索片段格式化为带编号的上下文，同时记录来源映射"""
    if not docs_with_scores:
        return "（知识库中暂无相关内容，请用你的知识正常回答用户问题）", []

    parts = []
    source_map = []  # [{"id": "[1]", "doc_name": ..., "content": ...}, ...]

    for i, (doc, score) in enumerate(docs_with_scores, 1):
        doc_name = doc.metadata.get("doc_name", "未知文档")
        marker = f"[{doc_name}]"
        parts.append(f"{marker}\n{doc.page_content}")
        source_map.append({
            "id": marker,
            "doc_name": doc_name,
            "content": doc.page_content[:200],
            "score": round(score, 4),
        })

    return "\n\n".join(parts), source_map


def _filter_used_sources(answer: str, source_map: List[Dict]) -> List[Dict]:
    """从 LLM 回答中反向匹配真正被引用的来源，按文档去重"""
    if not source_map:
        return []
    seen = set()
    used = []
    for src in source_map:
        if src["doc_name"] in seen:
            continue
        if src["id"] in answer or src["doc_name"] in answer:
            seen.add(src["doc_name"])
            used.append({
                "doc_name": src["doc_name"],
                "content": src["content"],
                "score": src["score"],
            })
    return used


async def rag_qa_stream(
    question: str,
    chat_history: List[Dict[str, str]] | None = None,
) -> AsyncIterator[Dict[str, Any]]:
    """RAG 问答流水线 - 极简快速版"""
    if chat_history is None:
        chat_history = []

    # 1. 向量检索（跳过问题改写，直接检索，省 1-3 秒）
    docs_with_scores = await similarity_search(question)

    # 过滤低相关性结果：分数低于阈值的丢弃
    RELEVANCE_THRESHOLD = 0.0  # 只过滤负分（明显不相关）
    docs_with_scores = [(d, s) for d, s in docs_with_scores if s >= RELEVANCE_THRESHOLD]

    # 2. 构建带标记的上下文
    context, source_map = _format_context(docs_with_scores)
    history_text = _format_chat_history(chat_history)

    # 3. 构建 Prompt
    prompt_text = SYSTEM_PROMPT.format(
        context=context,
        chat_history=history_text,
        question=question,
    )

    # 4. 流式生成
    llm = _get_llm(streaming=True)
    full_answer = ""

    async for chunk in llm.astream(prompt_text):
        if hasattr(chunk, "content") and chunk.content:
            full_answer += chunk.content
            yield {"type": "token", "content": chunk.content}

    # 5. 筛选真正被引用的来源
    used_sources = _filter_used_sources(full_answer, source_map)
    if used_sources:
        yield {"type": "sources", "sources": used_sources}

    yield {"type": "done", "full_answer": full_answer}
