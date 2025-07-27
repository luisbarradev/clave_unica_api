from fastapi import FastAPI
import os
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field, validator

from src.config.config import (
    RATE_LIMIT_SECONDS_HEALTH,
    RATE_LIMIT_SECONDS_SCRAPE,
    RATE_LIMIT_TIMES_HEALTH,
    RATE_LIMIT_TIMES_SCRAPE,
)
from src.config.logger import get_logger
from src.models.clave_unica import ClaveUnica
from src.queue.deduplicator import Deduplicator
from src.queue.models import Task
from src.queue.queue_manager import QueueManager
from src.facades.scraper_facade import ScraperFacade
from src.scrapers.captcha_solver import RecaptchaSolver
from src.scrapers.login_scraper import LoginScraper
from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy
from src.utils.rut_validator import validate_rut

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager for managing the lifespan of the FastAPI application.

    Initializes Redis connection and FastAPILimiter.
    """
    redis_host = os.getenv('REDISHOST', 'localhost')
    redis_port = int(os.getenv('REDISPORT', 6379))
    redis_password = os.getenv('REDISPASSWORD', None) or None

    redis_instance = redis.Redis(
        host=redis_host, port=redis_port, password=redis_password, encoding='utf-8', decode_responses=True
    )
    app.state.redis = redis_instance
    await FastAPILimiter.init(redis_instance)
    yield


app = FastAPI(
    lifespan=lifespan,
    title='API NO OFICIAL de Clave Única (Uso Personal)',
    description=(
        'Esta API permite automatizar, de forma local y personal, la extracción de datos desde servicios públicos '
        'chilenos como la CMF (Comisión para el Mercado Financiero), la AFC (Administradora de Fondos de Cesantía) '
        'y otros portales estatales, utilizando las credenciales de Clave Única del propio usuario.\n\n'
        '⚠️ Este proyecto es **open source**, está orientado exclusivamente a fines personales, educativos y de auditoría técnica. '
        'No debe utilizarse como servicio web para terceros. **No recolecta, almacena ni transmite credenciales.**\n\n'
        '🔐 Esta API **no está afiliada ni cuenta con autorización oficial del Estado de Chile ni de sus organismos** '
        '(Gobierno Digital, CMF, AFC, SII, etc.).\n\n'
        'Su propósito es visibilizar los riesgos actuales de automatización no regulada, promover el empoderamiento ciudadano '
        'sobre sus propios datos y fomentar el debate sobre el uso seguro, transparente y ético de la identidad digital.\n\n'
        '🛑 **Está terminantemente prohibido su uso comercial, institucional o para automatizar accesos a cuentas de terceros.** '
        'El uso indebido de esta herramienta es responsabilidad exclusiva de quien la ejecute.'
    ),
    version='1.0.0',
    license_info={'name': 'GPL-3.0', 'url': 'https://www.gnu.org/licenses/gpl-3.0.html'},
    contact={'name': 'Luis Francisco Barra', 'email': 'contacto@luisbarra.cl', 'url': 'https://www.luisbarra.cl'},
)


@app.get(
    '/health',
    tags=['Health'],
    dependencies=[Depends(RateLimiter(times=RATE_LIMIT_TIMES_HEALTH, seconds=RATE_LIMIT_SECONDS_HEALTH))],
)
async def health_check(request: Request):
    """Perform a health check of the API and its Redis connection."""
    redis_status = 'ok'
    try:
        await request.app.state.redis.ping()
    except Exception:
        redis_status = 'error'
    return {'status': 'ok', 'redis': redis_status}


queue_manager = QueueManager()
deduplicator = Deduplicator()


class CMFScraperRequest(BaseModel):
    """Request model for CMF scraper with username and password."""

    username: str = Field(..., description='Chilean RUT in XX.XXX.XXX-Y format')
    password: str = Field(..., min_length=6, description='Password for ClaveUnica, minimum 6 characters')

    @validator('username')
    def username_must_be_valid_rut(cls, v):  # noqa: N805
        """Validate the RUT format and checksum."""
        if not validate_rut(v):
            raise ValueError('Invalid RUT format or checksum')
        return v


class CMFScraperAsyncRequest(CMFScraperRequest):
    """Request model for asynchronous CMF scraper with webhook URL."""

    webhook_url: str = Field(..., description='URL to send the scraping results')


cmf_scrape_example_response = {
    'status': 'success',
    'data': {
        'debt_data': {
            'data': [
                {
                    'institution': 'Banco Santander',
                    'credit_type': 'Consumo',
                    'total_credit': 3500000,
                    'current': 3500000,
                    'late_30_59': 0,
                    'late_60_89': 0,
                    'late_90_plus': 0,
                }
            ],
            'totals': {
                'total_credit': 3500000,
                'current': 3500000,
                'late_30_59': 0,
                'late_60_89': 0,
                'late_90_plus': 0,
            },
            'timestamp': '2025-07-19T23:28:35.643908',
            'currency': 'CLP',
        },
        'line_of_credit_data': {
            'data': [
                {'institution': 'Banco de Chile', 'direct': 2800000, 'indirect': 0},
                {'institution': 'Banco BCI', 'direct': 1800000, 'indirect': 0},
                {'institution': 'Banco Falabella', 'direct': 1300000, 'indirect': 0},
                {'institution': 'Banco Ripley', 'direct': 1600000, 'indirect': 0},
            ],
            'totals': {'direct': 7500000, 'indirect': 0},
            'timestamp': '2025-07-19T23:28:35.673648',
            'currency': 'CLP',
        },
        'has_credit_lines': {'direct': True, 'indirect': False},
    },
}


@app.post(
    '/scrape/cmf',
    summary='Scrape CMF data',
    response_description='CMF data scraped successfully',
    tags=['sync'],
    responses={
        200: {
            'description': 'Successful Response',
            'content': {'application/json': {'example': cmf_scrape_example_response}},
        }
    },
)
async def scrape_cmf(request: CMFScraperRequest):
    """Scrape CMF data synchronously."""
    try:
        clave_unica = ClaveUnica(rut=request.username, password=request.password)

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

            data = await facade.scrape('cmf')
            await browser.close()
            return {'status': 'success', 'data': data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/scrape/afc', summary='Scrape AFC data', response_description='AFC data scraped successfully', tags=['sync'])
async def scrape_afc(request: CMFScraperRequest):
    """Scrape AFC data synchronously."""
    try:
        clave_unica = ClaveUnica(rut=request.username, password=request.password)

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

            data = await facade.scrape('afc')
            await browser.close()
            return {'status': 'success', 'data': data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


sii_scrape_example_response = {
    'status': 'success',
    'data': {
        'header_data': {'rut': '12345678-9', 'name': 'Juan Pérez', 'email': 'juan.perez@example.com'},
        'tax_declarations': [
            {'year': 2023, 'status': 'Vigente', 'income': 15000000},
            {'year': 2022, 'status': 'Vigente', 'income': 12000000},
        ],
    },
}


@app.post(
    '/scrape/sii',
    summary='Scrape SII data',
    response_description='SII data scraped successfully',
    tags=['sync'],
    responses={
        200: {
            'description': 'Successful Response',
            'content': {'application/json': {'example': sii_scrape_example_response}},
        }
    },
)
async def scrape_sii(request: CMFScraperRequest):
    """Scrape SII data synchronously."""
    try:
        clave_unica = ClaveUnica(rut=request.username, password=request.password)

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

            data = await facade.scrape('sii')
            await browser.close()
            return {'status': 'success', 'data': data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    '/async/scrape/cmf',
    summary='Scrape CMF data asynchronously',
    response_description='CMF scraping task accepted',
    tags=['async'],
)
async def async_scrape_cmf(request: CMFScraperAsyncRequest):
    """Scrape CMF data asynchronously by enqueuing a task."""
    if deduplicator.is_duplicate(request.username, request.webhook_url):
        logger.info(f'Duplicate task detected for user {request.username}. Rejecting.')
        return {'status': 'rejected', 'message': 'Duplicate task detected within the last 5 minutes.'}

    task_id = str(uuid.uuid4())
    task = Task(
        task_id=task_id,
        username=request.username,
        password=request.password,
        webhook_url=request.webhook_url,
        scraper_type='cmf',
        retries=0,
        max_retries=3,
    )
    queue_manager.enqueue(task)
    deduplicator.mark_as_processed(request.username, request.webhook_url)
    logger.info(f'Task {task_id} enqueued successfully for user {request.username}.')
    return {'status': 'accepted', 'task_id': task_id, 'message': 'CMF scraping task enqueued successfully'}


@app.post(
    '/async/scrape/afc',
    summary='Scrape AFC data asynchronously',
    dependencies=[Depends(RateLimiter(times=RATE_LIMIT_TIMES_SCRAPE, seconds=RATE_LIMIT_SECONDS_SCRAPE))],
    response_description='AFC scraping task accepted',
    tags=['async'],
)
async def async_scrape_afc(request: CMFScraperAsyncRequest):
    """Scrape AFC data asynchronously by enqueuing a task."""
    if deduplicator.is_duplicate(request.username, request.webhook_url):
        logger.info(f'Duplicate task detected for user {request.username}. Rejecting.')
        return {'status': 'rejected', 'message': 'Duplicate task detected within the last 5 minutes.'}

    task_id = str(uuid.uuid4())
    task = Task(
        task_id=task_id,
        username=request.username,
        password=request.password,
        webhook_url=request.webhook_url,
        scraper_type='afc',
        retries=0,
        max_retries=3,
    )
    queue_manager.enqueue(task)
    deduplicator.mark_as_processed(request.username, request.webhook_url)
    logger.info(f'Task {task_id} enqueued successfully for user {request.username}.')
    return {'status': 'accepted', 'task_id': task_id, 'message': 'AFC scraping task enqueued successfully'}


@app.post(
    '/async/scrape/sii',
    summary='Scrape SII data asynchronously',
    dependencies=[Depends(RateLimiter(times=RATE_LIMIT_TIMES_SCRAPE, seconds=RATE_LIMIT_SECONDS_SCRAPE))],
    response_description='SII scraping task accepted',
    tags=['async'],
)
async def async_scrape_sii(request: CMFScraperAsyncRequest):
    """Scrape SII data asynchronously by enqueuing a task."""
    if deduplicator.is_duplicate(request.username, request.webhook_url):
        logger.info(f'Duplicate task detected for user {request.username}. Rejecting.')
        return {'status': 'rejected', 'message': 'Duplicate task detected within the last 5 minutes.'}

    task_id = str(uuid.uuid4())
    task = Task(
        task_id=task_id,
        username=request.username,
        password=request.password,
        webhook_url=request.webhook_url,
        scraper_type='sii',
        retries=0,
        max_retries=3,
    )
    queue_manager.enqueue(task)
    deduplicator.mark_as_processed(request.username, request.webhook_url)
    logger.info(f'Task {task_id} enqueued successfully for user {request.username}.')
    return {'status': 'accepted', 'task_id': task_id, 'message': 'SII scraping task enqueued successfully'}
