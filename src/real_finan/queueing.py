from __future__ import annotations

import json
from dataclasses import dataclass, field

from redis import Redis


@dataclass
class RedisQueueManager:
    redis_url: str
    queue_name: str
    _redis: Redis = field(default=None, init=False, repr=False)

    def connection(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, socket_timeout=30, socket_connect_timeout=10)
        return self._redis

    def enqueue(self, payload: dict) -> None:
        Redis.from_url(self.redis_url).rpush(self.queue_name, json.dumps(payload, ensure_ascii=False))

    def dequeue(self, timeout_seconds: int = 5) -> dict | None:
        try:
            result = self.connection().blpop(self.queue_name, timeout=timeout_seconds)
        except Exception:
            self._redis = None
            return None
        if not result:
            return None
        _, raw_payload = result
        return json.loads(raw_payload.decode("utf-8"))
