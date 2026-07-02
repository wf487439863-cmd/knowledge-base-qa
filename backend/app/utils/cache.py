"""缓存工具 - 支持 Redis + 内存 LRU 双层缓存"""
import hashlib
import json
from typing import Optional
from cachetools import LRUCache
from app.config import get_settings

settings = get_settings()

# 内存 LRU 缓存 (最多 500 条)
memory_cache: LRUCache = LRUCache(maxsize=500)

# Redis 客户端 (懒加载)
_redis_client = None


def _get_redis():
    global _redis_client
    if not settings.REDIS_ENABLED:
        return None
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            return None
    return _redis_client


def _cache_key(question: str) -> str:
    """生成问题哈希作为缓存 key"""
    return "qa:" + hashlib.md5(question.strip().lower().encode()).hexdigest()


async def get_cached_answer(question: str) -> Optional[dict]:
    """从缓存中获取答案"""
    key = _cache_key(question)

    # 先查内存缓存
    if key in memory_cache:
        return memory_cache[key]

    # 再查 Redis
    redis = _get_redis()
    if redis:
        try:
            cached = await redis.get(key)
            if cached:
                data = json.loads(cached)
                memory_cache[key] = data
                return data
        except Exception:
            pass

    return None


async def set_cached_answer(question: str, answer_data: dict):
    """缓存答案"""
    key = _cache_key(question)

    # 写内存缓存
    memory_cache[key] = answer_data

    # 写 Redis (过期 1 小时)
    redis = _get_redis()
    if redis:
        try:
            await redis.setex(key, 3600, json.dumps(answer_data, ensure_ascii=False))
        except Exception:
            pass
