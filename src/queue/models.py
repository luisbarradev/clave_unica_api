from pydantic import BaseModel, Field
from typing import Any

class Task(BaseModel):
    task_id: str
    username: str
    password: str
    webhook_url: str
    scraper_type: str = Field(..., description="Type of scraper to use (e.g., 'cmf', 'afc')")
    data: Any = None
    retries: int = Field(0, description="Number of times this task has been retried")
    max_retries: int = Field(3, description="Maximum number of retries for this task")