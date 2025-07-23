import os
from typing import Optional

import redis

from src.queue.models import Task


class QueueManager:
    """Manages the task queue and dead-letter queue using Redis."""

    def __init__(self, queue_name='cmf_tasks', dlq_name='cmf_dlq'):
        host = os.getenv('REDISHOST', 'localhost')
        port = int(os.getenv('REDISPORT', 6379))
        password = os.getenv('REDISPASSWORD', None)
        # Keeping REDIS_DB as it's a common Redis client parameter
        db = int(os.getenv('REDIS_DB', 0))
        self.redis_client = redis.Redis(
            host=host, port=port, password=password, db=db)
        self.queue_name = queue_name
        self.dlq_name = dlq_name

    def enqueue(self, task: Task):
        """Enqueues a task into the main queue."""
        self.redis_client.rpush(self.queue_name, task.json())

    def dequeue(self) -> Optional[Task]:
        """Dequeues a task from the main queue."""
        task_json = self.redis_client.lpop(self.queue_name)
        if task_json:
            if isinstance(task_json, bytes):
                task_json = task_json.decode('utf-8')
            if isinstance(task_json, str):
                return Task.model_validate_json(task_json)
        return None

    def enqueue_dlq(self, task: Task):
        """Enqueues a task into the dead-letter queue."""
        self.redis_client.rpush(self.dlq_name, task.json())

    def is_empty(self) -> bool:
        """Check if the main queue is empty."""
        return bool(self.redis_client.llen(self.queue_name) == 0)

    def get_queue_size(self) -> int:
        """Return the current size of the main queue."""
        return int(self.redis_client.llen(self.queue_name))  # type: ignore
