import hashlib
import os

import redis


class Deduplicator:
    """Handles deduplication of tasks using Redis to prevent processing the same task multiple times."""

    def __init__(self, prefix='dedup:', ttl=300): # ttl in seconds (5 minutes)
        host = os.getenv('REDISHOST', 'localhost')
        port = int(os.getenv('REDISPORT', 6379))
        password = os.getenv('REDISPASSWORD', None)
        db = int(os.getenv('REDIS_DB', 0)) # Keeping REDIS_DB as it's a common Redis client parameter
        self.redis_client = redis.Redis(host=host, port=port, password=password, db=db)
        self.prefix = prefix
        self.ttl = ttl

    def _generate_key(self, username: str, webhook_url: str) -> str:
        # TODO: generate hash with path /cmf /afc etc
        # Create a hash based on relevant task parameters
        data_string = f"{username}-{webhook_url}"
        return str(self.prefix + hashlib.sha256(data_string.encode('utf-8')).hexdigest())

    def is_duplicate(self, username: str, webhook_url: str) -> bool:
        """Check if a task with the given username and webhook URL is a duplicate."""
        key = self._generate_key(username, webhook_url)
        if self.redis_client.exists(key):
            return True
        return False

    def mark_as_processed(self, username: str, webhook_url: str):
        """Mark a task as processed to prevent future duplicates."""
        key = self._generate_key(username, webhook_url)
        self.redis_client.setex(key, self.ttl, "1") # Store a dummy value, expire after ttl
