import asyncio
import requests
import logging
from playwright.async_api import async_playwright
from src.scrapers.CMF_scraper import CMFScraper
from src.scrapers.login_scraper import LoginScraper
from src.models.clave_unica import ClaveUnica
from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy
from src.queue.queue_manager import QueueManager


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_task(task, queue_manager: QueueManager):
    logging.info(f"Processing task: {task.task_id} (Attempt: {task.retries + 1}/{task.max_retries})")
    try:
        clave_unica = ClaveUnica(
            rut=task.username,
            password=task.password
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            login_scraper = LoginScraper(ClaveUnicaLoginStrategy())
            cmf_scraper = CMFScraper(context=context, login_scraper=login_scraper, clave_unica=clave_unica)
            
            data = await cmf_scraper.run()
            await browser.close()
            
            result = {"status": "success", "task_id": task.task_id, "data": data}
            logging.info(f"Task {task.task_id} completed. Sending to webhook: {task.webhook_url}")
            requests.post(task.webhook_url, json=result)
    except Exception as e:
        logging.error(f"Task {task.task_id} failed: {e}")
        task.retries += 1
        if task.retries < task.max_retries:
            logging.warning(f"Retrying task {task.task_id}. Retries left: {task.max_retries - task.retries}")
            # Exponential backoff: 2, 4, 8 seconds delay
            retry_delay = 2 ** task.retries
            await asyncio.sleep(retry_delay)
            queue_manager.enqueue(task) # Re-enqueue for retry
        else:
            logging.error(f"Task {task.task_id} failed after {task.max_retries} retries. Moving to DLQ.")
            error_result = {"status": "failed", "task_id": task.task_id, "detail": str(e), "retries_attempted": task.retries}
            requests.post(task.webhook_url, json=error_result) # Notify webhook of final failure
            queue_manager.enqueue_dlq(task) # Move to Dead Letter Queue

async def main():
    queue_manager = QueueManager()
    logging.info("Worker started. Listening for tasks...")
    while True:
        task = queue_manager.dequeue()
        if task:
            await process_task(task, queue_manager)
        await asyncio.sleep(1) # Wait for 1 second before checking the queue again

if __name__ == "__main__":
    asyncio.run(main())