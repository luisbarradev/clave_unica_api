import asyncio
import logging

import requests
from playwright.async_api import async_playwright

from src.facades.scraper_facade import ScraperFacade
from src.models.clave_unica import ClaveUnica
from src.queue.queue_manager import QueueManager
from src.scrapers.captcha_solver import RecaptchaSolver
from src.scrapers.login_scraper import LoginScraper
from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


async def process_task(task, queue_manager: QueueManager):
    """Processes a single task from the queue."""
    logging.info(
        f"Processing task: {task.task_id} (Attempt: {task.retries + 1}/{task.max_retries})")
    try:
        clave_unica = ClaveUnica(
            rut=task.username,
            password=task.password
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            login_scraper = LoginScraper(ClaveUnicaLoginStrategy())
            facade = ScraperFacade(
                context=context,
                login_scraper=login_scraper,
                clave_unica=clave_unica,
                captcha_solver=RecaptchaSolver(),
            )
            data = await facade.scrape(task.scraper_type)

            await browser.close()

            result = {"status": "success",
                      "task_id": task.task_id, "data": data}
            logging.info(
                f"Task {task.task_id} completed. Sending to webhook: {task.webhook_url}")
            requests.post(task.webhook_url, json=result)
    except Exception as e:
        logging.error(f"Task {task.task_id} failed: {e}")
        task.retries += 1
        if task.retries < task.max_retries:
            logging.warning(
                f"Retrying task {task.task_id}. Retries left: {task.max_retries - task.retries}")
            # Exponential backoff: 2, 4, 8 seconds delay
            retry_delay = 2 ** task.retries
            await asyncio.sleep(retry_delay)
            queue_manager.enqueue(task)  # Re-enqueue for retry
        else:
            logging.error(
                f"Task {task.task_id} failed after {task.max_retries} retries. Moving to DLQ.")
            error_result = {"status": "failed", "task_id": task.task_id, "detail": str(e),
                            "retries_attempted": task.retries}
            # Notify webhook of final failure
            requests.post(task.webhook_url, json=error_result)
            queue_manager.enqueue_dlq(task)  # Move to Dead Letter Queue


async def main():
    """Main function for the worker that continuously processes tasks from the queue."""
    queue_manager = QueueManager()
    logging.info("Worker started. Listening for tasks...")
    while True:
        task = queue_manager.dequeue()
        if task:
            await process_task(task, queue_manager)
        # Wait for 1 second before checking the queue again
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
