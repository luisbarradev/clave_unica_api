
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import re
from typing import List
from playwright.async_api import Page, BrowserContext, TimeoutError
from src.config.config import NETWORK_IDLE_TIMEOUT
from src.scrapers.login_scraper import LoginScraper
from src.utils.utils import parse_money
from src.config.logger import get_logger, log_execution_func
from src.dto.cmf_data import CMFScraperResult, DebtEntry, DebtTotals
from src.utils.exceptions import ScraperDataExtractionError, SelectorNotFoundError


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
        debt_data: CMFScraperResult = {
            "data": [],
            "totals": {
                'total_credit': 0,
                'current': 0,
                'late_30_59': 0,
                'late_60_89': 0,
                'late_90_plus': 0
            }
        }

        try:
            if await self.have_debt(page):
                debt_data = await self.extract_debt(page)
        except (SelectorNotFoundError, ScraperDataExtractionError) as e:
            logger.error(f"Error during CMF data extraction: {e}")
            # Depending on requirements, you might re-raise or return partial data
            # For now, we'll return the initial empty debt_data

        return {
            "debt_data": debt_data
        }

    @log_execution_func
    async def have_debt(self, page: Page) -> bool:
        try:
            await page.wait_for_selector("#cmfDeuda_resumen_deuda .fs-44", timeout=NETWORK_IDLE_TIMEOUT)
            debt_selector = page.locator("#cmfDeuda_resumen_deuda .fs-44")
            text = await debt_selector.inner_text()
            debt = parse_money(text)
            return debt > 0
        except TimeoutError as e:
            logger.error(f"Debt selector not found: {e}")
            raise SelectorNotFoundError("Debt selector not found.") from e

    @log_execution_func
    async def extract_debt(self, page: Page) -> CMFScraperResult:
        """Extracts CMF debt table by financial institution, including totals."""
        try:
            await page.wait_for_selector("#tabla_deuda_directa", timeout=NETWORK_IDLE_TIMEOUT)

            # Select tbody rows (institution-level data)
            body_rows = page.locator(
                "#tabla_deuda_directa tbody#tabla_deuda_directa_data tr")
            body_count = await body_rows.count()

            # Select tfoot row (totals)
            footer_row = page.locator("#tabla_deuda_directa tfoot tr.tr-totales")

            results: List[DebtEntry] = []

            # Extract data rows
            for i in range(body_count):
                row = body_rows.nth(i)
                cells = await row.locator("td").all_text_contents()

                if len(cells) < 7:
                    logger.warning(f"Row {i} has less than 7 cells. Skipping.")
                    continue

                try:
                    results.append(DebtEntry({
                        "institution": cells[0].strip(),
                        "credit_type": cells[1].strip(),
                        "total_credit": parse_money(cells[2]),
                        "current": parse_money(cells[3]),
                        "late_30_59": parse_money(cells[4]),
                        "late_60_89": parse_money(cells[5]),
                        "late_90_plus": parse_money(cells[6]),
                    }))
                except ValueError as e:
                    logger.error(f"Error parsing money in row {i}: {e}. Row data: {cells}")
                    raise ScraperDataExtractionError(f"Error parsing money in row {i}") from e

            # Extract totals
            total_cells = await footer_row.locator("td").all_text_contents()

            # Define a helper to safely get and parse a cell, logging a warning if missing
            def get_parsed_total(index: int, field_name: str) -> int:
                if len(total_cells) > index:
                    try:
                        return parse_money(total_cells[index])
                    except ValueError as e:
                        logger.error(f"Could not parse '{field_name}' from cell at index {index}. Value: '{total_cells[index]}'.")
                        raise ScraperDataExtractionError(f"Error parsing total for {field_name}") from e
                else:
                    logger.error(f"Missing '{field_name}' cell at index {index}.")
                    raise ScraperDataExtractionError(f"Missing total cell for {field_name}")

            totals: DebtTotals = {
                "total_credit": get_parsed_total(2, "total_credit"),
                "current": get_parsed_total(3, "current"),
                "late_30_59": get_parsed_total(4, "late_30_59"),
                "late_60_89": get_parsed_total(5, "late_60_89"),
                "late_90_plus": get_parsed_total(6, "late_90_plus"),
            }

            return CMFScraperResult({
                "data": results,
                "totals": totals
            })
        except TimeoutError as e:
            logger.error(f"Debt table not found: {e}")
            raise SelectorNotFoundError("Debt table not found.") from e
