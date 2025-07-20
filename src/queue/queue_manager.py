import redis
import json
import os
from typing import Optional
from src.queue.models import Task

class QueueManager:
    def __init__(self, queue_name='cmf_tasks', dlq_name='cmf_dlq'):
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', 6379))
        db = int(os.getenv('REDIS_DB', 0))
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        self.queue_name = queue_name
        self.dlq_name = dlq_name

    def enqueue(self, task: Task):
        self.redis_client.rpush(self.queue_name, task.json())

    def dequeue(self) -> Optional[Task]:
        task_json = self.redis_client.lpop(self.queue_name)
        if task_json:
            return Task.parse_raw(task_json)
        return None

    def enqueue_dlq(self, task: Task):
        self.redis_client.rpush(self.dlq_name, task.json())

    def is_empty(self) -> bool:
        return self.redis_client.llen(self.queue_name) == 0

    def get_queue_size(self) -> int:
        return self.redis_client.llen(self.queue_name)