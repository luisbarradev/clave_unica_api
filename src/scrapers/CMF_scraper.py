
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import re
from playwright.async_api import Page, BrowserContext
from src.config.config import NETWORK_IDLE_TIMEOUT
from src.scrapers.login_scraper import LoginScraper
from src.utils.utils import parse_money
from src.config.logger import get_logger, log_execution_func


LOGIN_URL = 'https://conocetudeuda.cmfchile.cl/mediador/claveunica/'

logger = get_logger(__name__)

class CMFScraper:

    def __init__(self, context: BrowserContext, login_scraper: LoginScraper):
        self.login_scraper = login_scraper
        self.context = context

    @log_execution_func
    async def __login(self, page: Page):
        await page.goto(LOGIN_URL)
        await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
        await self.login_scraper.do_login(page)
        await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)

    @log_execution_func
    async def run(self):
        page = await self.context.new_page()
        await self.__login(page)
        debt_data = {
            "data": [],
            "totals": {
                'total_credit': 0,
                'current': 0,
                'late_30_59': 0,
                'late_60_89': 0,
                'late_90_plus': 0
            }
        }

        if await self.have_debt(page):
            debt_data = await self.extract_debt(page)

        return {
            "debt_data": debt_data
        }

    @log_execution_func
    async def have_debt(self, page: Page) -> bool:
        await page.wait_for_selector("#cmfDeuda_resumen_deuda .fs-44")
        debt_selector = page.locator("#cmfDeuda_resumen_deuda .fs-44")
        text = await debt_selector.inner_text()
        debt = parse_money(text)
        return debt > 0

    @log_execution_func
    async def extract_debt(self, page: Page) -> dict:
        """Extracts CMF debt table by financial institution, including totals."""

        await page.wait_for_selector("#tabla_deuda_directa")

        # Select tbody rows (institution-level data)
        body_rows = page.locator(
            "#tabla_deuda_directa tbody#tabla_deuda_directa_data tr")
        body_count = await body_rows.count()

        # Select tfoot row (totals)
        footer_row = page.locator("#tabla_deuda_directa tfoot tr.tr-totales")

        results = []

        # Extract data rows
        for i in range(body_count):
            row = body_rows.nth(i)
            cells = await row.locator("td").all_text_contents()

            if len(cells) < 7:
                continue

            results.append({
                "institution": cells[0].strip(),
                "credit_type": cells[1].strip(),
                "total_credit": parse_money(cells[2]),
                "current": parse_money(cells[3]),
                "late_30_59": parse_money(cells[4]),
                "late_60_89": parse_money(cells[5]),
                "late_90_plus": parse_money(cells[6]),
            })

        # Extract totals
        total_cells = await footer_row.locator("td").all_text_contents()

        totals = {
            "total_credit": parse_money(total_cells[2]) if len(total_cells) > 2 else 0,
            "current": parse_money(total_cells[3]) if len(total_cells) > 3 else 0,
            "late_30_59": parse_money(total_cells[4]) if len(total_cells) > 4 else 0,
            "late_60_89": parse_money(total_cells[5]) if len(total_cells) > 5 else 0,
            "late_90_plus": parse_money(total_cells[6]) if len(total_cells) > 6 else 0,
        }

        return {
            "data": results,
            "totals": totals
        }
