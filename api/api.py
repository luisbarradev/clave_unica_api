from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from playwright.async_api import async_playwright
from src.scrapers.CMF_scraper import CMFScraper
from src.scrapers.login_scraper import LoginScraper
from src.models.clave_unica import ClaveUnica
from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy
import uuid
import asyncio
import requests
import logging
from src.queue.queue_manager import QueueManager
from src.queue.models import Task
from src.queue.deduplicator import Deduplicator
from src.utils.rut_validator import validate_rut

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

queue_manager = QueueManager()
deduplicator = Deduplicator()

class CMFScraperRequest(BaseModel):
    username: str = Field(..., description="Chilean RUT in XX.XXX.XXX-Y format")
    password: str = Field(..., min_length=6, description="Password for ClaveUnica, minimum 6 characters")

    @validator('username')
    def username_must_be_valid_rut(cls, v):
        if not validate_rut(v):
            raise ValueError('Invalid RUT format or checksum')
        return v

class CMFScraperAsyncRequest(CMFScraperRequest):
    webhook_url: str = Field(..., description="URL to send the scraping results")

cmf_scrape_example_response = {
    "status": "success",
    "data": {
        "debt_data": {
            "data": [
                {
                    "institution": "Banco Santander",
                    "credit_type": "Consumo",
                    "total_credit": 3500000,
                    "current": 3500000,
                    "late_30_59": 0,
                    "late_60_89": 0,
                    "late_90_plus": 0
                }
            ],
            "totals": {
                "total_credit": 3500000,
                "current": 3500000,
                "late_30_59": 0,
                "late_60_89": 0,
                "late_90_plus": 0
            },
            "timestamp": "2025-07-19T23:28:35.643908",
            "currency": "CLP"
        },
        "line_of_credit_data": {
            "data": [
                {
                    "institution": "Banco de Chile",
                    "direct": 2800000,
                    "indirect": 0
                },
                {
                    "institution": "Banco BCI",
                    "direct": 1800000,
                    "indirect": 0
                },
                {
                    "institution": "Banco Falabella",
                    "direct": 1300000,
                    "indirect": 0
                },
                {
                    "institution": "Banco Ripley",
                    "direct": 1600000,
                    "indirect": 0
                }
            ],
            "totals": {
                "direct": 7500000,
                "indirect": 0
            },
            "timestamp": "2025-07-19T23:28:35.673648",
            "currency": "CLP"
        },
        "has_credit_lines": {
            "direct": True,
            "indirect": False
        }
    }
}

@app.post("/scrape/cmf",
    summary="Scrape CMF data",
    response_description="CMF data scraped successfully",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": cmf_scrape_example_response
                }
            }
        }
    }
)
async def scrape_cmf(request: CMFScraperRequest):
    try:
        clave_unica = ClaveUnica(
            rut=request.username,
            password=request.password
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            login_scraper = LoginScraper(ClaveUnicaLoginStrategy())
            cmf_scraper = CMFScraper(context=context, login_scraper=login_scraper, clave_unica=clave_unica)
            
            data = await cmf_scraper.run()
            await browser.close()
            return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/async/scrape/cmf",
    summary="Scrape CMF data asynchronously",
    response_description="CMF scraping task accepted",
)
async def async_scrape_cmf(request: CMFScraperAsyncRequest):
    if deduplicator.is_duplicate(request.username, request.webhook_url):
        logging.info(f"Duplicate task detected for user {request.username}. Rejecting.")
        return {"status": "rejected", "message": "Duplicate task detected within the last 5 minutes."}

    task_id = str(uuid.uuid4())
    task = Task(
        task_id=task_id,
        username=request.username,
        password=request.password,
        webhook_url=request.webhook_url
    )
    queue_manager.enqueue(task)
    deduplicator.mark_as_processed(request.username, request.webhook_url)
    logging.info(f"Task {task_id} enqueued successfully for user {request.username}.")
    return {"status": "accepted", "task_id": task_id, "message": "CMF scraping task enqueued successfully"}




