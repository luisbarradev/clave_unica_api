import redis
import hashlib
import json
import os

class Deduplicator:
    def __init__(self, prefix='dedup:', ttl=300): # ttl in seconds (5 minutes)
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', 6379))
        db = int(os.getenv('REDIS_DB', 0))
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        self.prefix = prefix
        self.ttl = ttl

    def _generate_key(self, username: str, webhook_url: str) -> str:
        # TODO: generate hash with path /cmf /afc etc
        # Create a hash based on relevant task parameters
        data_string = f"{username}-{webhook_url}"
        return self.prefix + hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    def is_duplicate(self, username: str, webhook_url: str) -> bool:
        key = self._generate_key(username, webhook_url)
        if self.redis_client.exists(key):
            return True
        return False

    def mark_as_processed(self, username: str, webhook_url: str):
        key = self._generate_key(username, webhook_url)
        self.redis_client.setex(key, self.ttl, "1") # Store a dummy value, expire after ttl