
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from typing import List
import re
from datetime import datetime
from playwright.async_api import Page, BrowserContext, TimeoutError
from src.config.config import NETWORK_IDLE_TIMEOUT
from src.scrapers.login_scraper import LoginScraper
from src.utils.utils import parse_money
from src.config.logger import get_logger, log_execution_func
from src.dto.cmf_data import CMFLineOfCreditResult, CMFScraperResult, DebtEntry, DebtTotals, HasCreditLinesResult, LineOfCreditEntry, LineOfCreditTotals
from src.utils.exceptions import ScraperDataExtractionError, SelectorNotFoundError


LOGIN_URL = 'https://conocetudeuda.cmfchile.cl/mediador/claveunica/'

logger = get_logger(__name__)

# Constants for CMF table headers
INSTITUTION_HEADER = "Institución financiera"
CREDIT_TYPE_HEADER = "Tipo de crédito"
TOTAL_CREDIT_HEADER = "Total del crédito"
CURRENT_HEADER = "Vigente"
LATE_30_59_HEADER = "30 a 59 días"
LATE_60_89_HEADER = "60 a 89 días"
LATE_90_PLUS_HEADER = "90 o más días"


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
            },
            "timestamp": datetime.now().isoformat(),
            "currency": "CLP"
        }

        try:
            if await self.have_debt(page):
                debt_data = await self.extract_debt(page)
        except (SelectorNotFoundError, ScraperDataExtractionError) as e:
            logger.error(f"Error during CMF data extraction: {e}")
            raise  # Re-raise the exception as it's a critical failure

        line_of_credit_data: CMFLineOfCreditResult = {
            "data": [],
            "totals": {
                'direct': 0,
                'indirect': 0
            },
            "timestamp": datetime.now().isoformat(),
            "currency": "CLP"
        }
        has_credit_lines_result: HasCreditLinesResult = {
            "direct": False,
            "indirect": False
        }

        try:
            has_credit_lines_result = await self.has_credit_lines(page)
            if has_credit_lines_result["direct"] or has_credit_lines_result["indirect"]:
                line_of_credit_data = await self.extract_line_of_credit(page)
        except (SelectorNotFoundError, ScraperDataExtractionError) as e:
            logger.error(
                f"Error during CMF line of credit data extraction: {e}")
            # Do not re-raise, as debt data might still be valid

        return {
            "debt_data": debt_data,
            "line_of_credit_data": line_of_credit_data,
            "has_credit_lines": has_credit_lines_result
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

            # Extract headers to create a dynamic mapping
            header_elements = await page.locator("#tabla_deuda_directa thead th").all()
            headers = []
            for header_el in header_elements:
                text = await header_el.inner_text()
                # Clean up header text (remove newlines, extra spaces, and 'de atraso' from specific columns)
                cleaned_text = text.replace("\n", " ").strip()
                if "días de atraso" in cleaned_text:
                    cleaned_text = cleaned_text.replace(
                        "de atraso", "").strip()
                headers.append(cleaned_text)

            # Create a mapping from cleaned header name to its index
            header_map = {
                INSTITUTION_HEADER: "institution",
                CREDIT_TYPE_HEADER: "credit_type",
                TOTAL_CREDIT_HEADER: "total_credit",
                CURRENT_HEADER: "current",
                LATE_30_59_HEADER: "late_30_59",
                LATE_60_89_HEADER: "late_60_89",
                LATE_90_PLUS_HEADER: "late_90_plus",
            }

            # Build index map based on actual headers
            index_map = {}
            for i, header_name in enumerate(headers):
                if header_name in header_map:
                    index_map[header_map[header_name]] = i

            # Validate that all expected headers are found
            expected_keys = set(header_map.values())
            found_keys = set(index_map.keys())
            if not expected_keys.issubset(found_keys):
                missing_keys = expected_keys - found_keys
                logger.error(
                    f"Missing expected headers in CMF debt table: {missing_keys}")
                raise ScraperDataExtractionError(
                    f"Missing expected headers in CMF debt table: {missing_keys}")

            # Select tbody rows (institution-level data)
            body_rows = page.locator(
                "#tabla_deuda_directa tbody#tabla_deuda_directa_data tr")
            body_count = await body_rows.count()

            # Select tfoot row (totals)
            footer_row = page.locator(
                "#tabla_deuda_directa tfoot tr.tr-totales")

            results: List[DebtEntry] = []

            # Extract data rows
            for i in range(body_count):
                row = body_rows.nth(i)
                cells = await row.locator("td").all_text_contents()

                # Ensure we have enough cells before trying to access them by index
                if len(cells) < max(index_map.values()) + 1:
                    logger.warning(
                        f"Row {i} has fewer cells than expected. Skipping.")
                    continue

                try:
                    results.append(DebtEntry({
                        "institution": cells[index_map["institution"]].strip(),
                        "credit_type": cells[index_map["credit_type"]].strip(),
                        "total_credit": parse_money(cells[index_map["total_credit"]]),
                        "current": parse_money(cells[index_map["current"]]),
                        "late_30_59": parse_money(cells[index_map["late_30_59"]]),
                        "late_60_89": parse_money(cells[index_map["late_60_89"]]),
                        "late_90_plus": parse_money(cells[index_map["late_90_plus"]]),
                    }))
                except ValueError as e:
                    logger.error(
                        f"Error parsing money in row {i}: {e}. Row data: {cells}")
                    raise ScraperDataExtractionError(
                        f"Error parsing money in row {i}") from e

            # Extract totals
            total_cells = await footer_row.locator("td").all_text_contents()

            # Define a helper to safely get and parse a cell, logging a warning if missing
            def get_parsed_total(field_key: str) -> int:
                index = index_map.get(field_key)
                if index is None or len(total_cells) <= index:
                    logger.error(
                        f"Missing total cell for '{field_key}' at expected index {index}.")
                    raise ScraperDataExtractionError(
                        f"Missing total cell for {field_key}")
                try:
                    return parse_money(total_cells[index])
                except ValueError as e:
                    logger.error(
                        f"Could not parse '{field_key}' from cell at index {index}. Value: '{total_cells[index]}'.")
                    raise ScraperDataExtractionError(
                        f"Error parsing total for {field_key}") from e

            totals: DebtTotals = {
                "total_credit": get_parsed_total("total_credit"),
                "current": get_parsed_total("current"),
                "late_30_59": get_parsed_total("late_30_59"),
                "late_60_89": get_parsed_total("late_60_89"),
                "late_90_plus": get_parsed_total("late_90_plus"),
            }

            return CMFScraperResult({
                "data": results,
                "totals": totals,
                "timestamp": datetime.now().isoformat(),
                "currency": "CLP"
            })
        except TimeoutError as e:
            logger.error(f"Debt table not found: {e}")
            raise SelectorNotFoundError("Debt table not found.") from e

    @log_execution_func
    async def extract_line_of_credit(self, page: Page) -> CMFLineOfCreditResult:
        """Extracts line of credit data from CMF table by financial institution."""
        try:
            await page.wait_for_selector("#tabla_lineas_credito", timeout=NETWORK_IDLE_TIMEOUT)

            table = page.locator("#tabla_lineas_credito")

            # Extract body rows
            body_rows = table.locator("tbody tr")
            row_count = await body_rows.count()

            results: List[LineOfCreditEntry] = []

            for i in range(row_count):
                row = body_rows.nth(i)
                cells = await row.locator("td").all_text_contents()

                if len(cells) != 3:
                    logger.warning(
                        f"Unexpected number of columns in row {i}: {len(cells)}. Skipping.")
                    continue

                try:
                    results.append({
                        "institution": cells[0].strip(),
                        "direct": parse_money(cells[1]),
                        "indirect": parse_money(cells[2]),
                    })
                except ValueError as e:
                    logger.error(
                        f"Error parsing money in line of credit row {i}: {e}. Row data: {cells}")
                    raise ScraperDataExtractionError(
                        f"Error parsing money in line of credit row {i}") from e

            # Extract totals
            footer_cells = await table.locator("tfoot tr.tr-totales td").all_text_contents()

            if len(footer_cells) != 3:
                logger.error(
                    f"Unexpected number of total columns: {len(footer_cells)}")
                raise ScraperDataExtractionError(
                    "Unexpected structure in totals row of line of credit table.")

            try:
                totals: LineOfCreditTotals = {
                    "direct": parse_money(footer_cells[1]),
                    "indirect": parse_money(footer_cells[2]),
                }
            except ValueError as e:
                logger.error(
                    f"Error parsing totals in line of credit table: {e}. Data: {footer_cells}")
                raise ScraperDataExtractionError(
                    "Error parsing line of credit totals") from e

            return {
                "data": results,
                "totals": totals,
                "timestamp": datetime.now().isoformat(),
                "currency": "CLP"
            }

        except TimeoutError as e:
            logger.error(f"Line of credit table not found: {e}")
            raise SelectorNotFoundError(
                "Line of credit table not found.") from e

    @log_execution_func
    async def has_credit_lines(self, page: Page) -> HasCreditLinesResult:
        """
        Checks if the user has any available direct or indirect credit lines.
        Returns a dict with booleans indicating availability.
        Looks specifically inside the #cmfDeuda_creditos_disponibles section.
        """
        try:
            container = page.locator("#cmfDeuda_creditos_disponibles")

            # Subsección de líneas de crédito dentro del contenedor principal
            section = container.locator("div.col-sm-6.mb-3.pr-xl-4")

            no_info = section.locator("p.alert.alert-light.border")
            if await no_info.count() > 0:
                text = (await no_info.first.inner_text()).strip()
                if "No registra información" in text:
                    return {"direct": False, "indirect": False}

            table = section.locator("table#tabla_lineas_credito")
            if await table.count() == 0:
                return {"direct": False, "indirect": False}

            rows = table.locator("tbody tr")
            row_count = await rows.count()

            direct_total = 0
            indirect_total = 0

            for i in range(row_count):
                row = rows.nth(i)
                cells = await row.locator("td").all_text_contents()
                if len(cells) != 3:
                    continue

                try:
                    direct_total += parse_money(cells[1])
                    indirect_total += parse_money(cells[2])
                except ValueError as e:
                    logger.warning(
                        f"Error parsing row {i} in credit line table: {e}")

            return {
                "direct": direct_total > 0,
                "indirect": indirect_total > 0
            }

        except Exception as e:
            logger.error(f"Error checking credit line availability: {e}")
            return {"direct": False, "indirect": False}
