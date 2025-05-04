# orchestrator/app/agents/memory/buffer_memory.py

import logging
from typing import List

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

class BufferMemory:
    """
    Keeps a rolling window of the last `MEMORY_BUFFER_MAX_LEN`
    user+bot exchanges per chat, stored in Redis.
    """

    def __init__(self):
        # Create a single shared Redis connection
        # `decode_responses=True` so we get back Python strings
        self.redis: Redis = Redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        # how many total entries (user+bot) to keep
        self.maxlen = settings.MEMORY_BUFFER_MAX_LEN * 2
        self.key_prefix = settings.MEMORY_BUFFER_KEY_PREFIX

    def _key(self, chat_id: int) -> str:
        return f"{self.key_prefix}{chat_id}"

    async def add(self, chat_id: int, speaker: str, text: str) -> None:
        """
        Push one entry at the tail, then trim list to last `maxlen`.
        Speaker should be 'user' or 'bot'.
        Stored format is e.g. "USER: Hello"
        """
        key = self._key(chat_id)
        entry = f"{speaker.upper()}: {text}"
        try:
            await self.redis.rpush(key, entry)
            # keep only the last `maxlen` entries
            await self.redis.ltrim(key, -self.maxlen, -1)
        except Exception as e:
            logger.error("BufferMemory.add failed: %s", e)

    async def get_history(self, chat_id: int) -> List[str]:
        """
        Returns the list of stored lines, oldest first:
          ["USER: hello", "BOT: hi there", ...]
        """
        key = self._key(chat_id)
        try:
            return await self.redis.lrange(key, 0, -1)
        except Exception as e:
            logger.error("BufferMemory.get_history failed: %s", e)
            return []
