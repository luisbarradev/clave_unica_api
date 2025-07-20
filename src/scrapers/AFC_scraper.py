from src.scrapers.captcha_solver import RecaptchaSolver
from src.scrapers.base_scraper import BaseScraper
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import logging
import os
from typing import Dict, List

import datetime

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page, BrowserContext
from playwright_recaptcha import recaptchav2

from src.config.logger import get_logger, log_execution_func
from src.models.clave_unica import ClaveUnica
from src.scrapers.login_scraper import LoginScraper
from src.utils.exceptions import ScraperDataExtractionError
from src.dto.afc_data import AFCScraperResult, AFCEmpresaEntry, AFCCotizacionEntry
from src.utils.utils import parse_money

logger = get_logger(__name__)


class AFCScraper(BaseScraper):
    """Scraper for AFC financial data."""

    def __init__(self, context: BrowserContext, login_scraper: LoginScraper, clave_unica: ClaveUnica, captcha_solver: RecaptchaSolver):
        self.context = context
        self.login_scraper = login_scraper
        self.clave_unica = clave_unica
        self.captcha_solver = captcha_solver

    @log_execution_func
    async def run(self) -> AFCScraperResult:
        """Scrapes AFC data from the given page."""
        page = await self.context.new_page()
        await page.goto(
            "https://webafiliados.afc.cl/WUI.AAP.OVIRTUAL/Default.aspx"
        )

        await self.captcha_solver.solve(page)

        await page.locator("input#btnCU").click()
        await page.wait_for_load_state('networkidle')

        login_success = await self.login_scraper.do_login(page, self.clave_unica)

        if not login_success:
            logger.error(
                "ClaveÚnica login failed during AFC scraping. "
            )
            raise ValueError("ClaveÚnica login failed during AFC scraping.")

        companies_data = await self.scrape_empresas(page)

        current_year = datetime.datetime.now().year
        years_to_scrape = [str(current_year - 2), str(current_year - 3)]
        contributions_data = await self.scrape_cotizaciones(page, years_to_scrape)

        return AFCScraperResult(
            companies_data=companies_data,
            contributions_data=contributions_data,
            timestamp=datetime.datetime.now().isoformat(),
            currency="CLP"
        )

    @log_execution_func
    async def scrape_empresas(self, page: Page) -> List[AFCEmpresaEntry]:
        """Scrapes AFC empresas data."""
        await page.goto(
            "https://webafiliados.afc.cl/WUI.AAP.OVIRTUAL/WebAfiliados/Datos/Empresas.aspx"
        )
        await page.wait_for_load_state('networkidle')
        await page.wait_for_selector(
            "table#contentPlaceHolder_gvEmpresas", timeout=10000
        )

        companies_data: List[AFCEmpresaEntry] = []
        table_element = await page.locator(
            "table#contentPlaceHolder_gvEmpresas"
        ).element_handle()

        if table_element:
            table_html = await table_element.inner_html()
            soup = BeautifulSoup(
                f'<table id="contentPlaceHolder_gvEmpresas">{table_html}</table>',
                "html.parser"
            )
            table = soup.find("table", id="contentPlaceHolder_gvEmpresas")

            if isinstance(table, Tag):
                headers = [
                    th.get_text(strip=True) for th in table.find_all("th")
                ]
                rows = []
                for tr in table.find_all("tr"):  # Skip header row
                    if not isinstance(tr, Tag):
                        continue
                    cols = [
                        td.get_text(strip=True) for td in tr.find_all("td")
                    ]
                    if cols:  # Only process rows with columns
                        row_data = {}
                        for i, header in enumerate(headers):
                            if i < len(cols):
                                row_data[header] = cols[i]
                        rows.append(row_data)

                # Map generic dict to AFCEmpresaEntry
                for row in rows:
                    companies_data.append(AFCEmpresaEntry(
                        employer_rut=row.get("RUT Empleador", ""),
                        employer_name=row.get("Razón Social", ""),
                        start_date=row.get("Fecha Inicio", ""),
                        end_date=row.get("Fecha Término", ""),
                        status=row.get("Estado", "")
                    ))
            else:
                logger.warning(
                    "Table not found or is not a valid HTML table element. "
                )
        else:
            logger.warning(
                "Table element not found by Playwright."
            )

        title = await page.title()
        return companies_data

    @log_execution_func
    async def scrape_cotizaciones(self, page: Page, years_to_scrape: list[str]) -> Dict[str, List[AFCCotizacionEntry]]:
        """Scrapes AFC cotizaciones data for specified years."""
        all_cotizaciones_data: Dict[str, List[AFCCotizacionEntry]] = {}

        current_year = datetime.datetime.now().year
        initial_url = f"https://webafiliados.afc.cl/WUI.AAP.OVIRTUAL/WebAfiliados/Certificados/CrtPagadas.aspx?periodo={current_year}"
        await page.goto(initial_url)
        await page.wait_for_load_state('networkidle')

        # Extract data for the initially displayed period (current year and previous year)
        initial_cotizaciones_data = await self._extract_cotizaciones_table(page, str(current_year))
        all_cotizaciones_data[str(current_year)] = initial_cotizaciones_data

        # Check if previous year's data is already included in the initial load
        # This assumes the initial load for current_year also includes current_year-1
        if str(current_year - 1) in years_to_scrape and str(current_year - 1) not in all_cotizaciones_data:
            # If not explicitly extracted, assume it's part of the initial load
            # and add it to the results if it's one of the requested years.
            # This part might need refinement based on actual data structure.
            pass  # Data for current_year-1 is expected to be in initial_cotizaciones_data

        # Iterate through the remaining years to scrape
        for year_to_scrape in years_to_scrape:
            if year_to_scrape == str(current_year):
                continue

            # If the previous year is already covered by the initial load, skip it here
            if year_to_scrape == str(current_year - 1) and str(current_year - 1) in all_cotizaciones_data:
                continue

            logger.info(f"Scraping cotizaciones for year: {year_to_scrape}")
            await page.select_option("select#contentPlaceHolder_ddlPeriodo", value=year_to_scrape)

            # Trigger the postback directly
            logger.info("Triggering postback for cotizaciones search...")
            await page.evaluate("__doPostBack('ctl00$contentPlaceHolder_btnBuscar','')")
            await page.wait_for_selector(
                "table#contentPlaceHolder_dgBusqueda", timeout=30000
            )

            cotizaciones_data_for_year = await self._extract_cotizaciones_table(page, year_to_scrape)
            all_cotizaciones_data[year_to_scrape] = cotizaciones_data_for_year

        title = await page.title()
        current_url = page.url
        return all_cotizaciones_data

    @log_execution_func
    async def _extract_cotizaciones_table(self, page: Page, year: str) -> List[AFCCotizacionEntry]:
        """Helper method to extract data from the cotizaciones table."""
        await page.wait_for_selector(
            "table#contentPlaceHolder_dgBusqueda", timeout=30000
        )

        cotizaciones_data: List[AFCCotizacionEntry] = []
        table_element = await page.locator(
            "table#contentPlaceHolder_dgBusqueda"
        ).element_handle()

        if table_element:
            table_html = await table_element.inner_html()
            soup = BeautifulSoup(
                f'<table id="contentPlaceHolder_dgBusqueda">{table_html}</table>',
                "html.parser"
            )
            table = soup.find("table", id="contentPlaceHolder_dgBusqueda")

            if isinstance(table, Tag):
                headers = [
                    th.get_text(strip=True) for th in table.find_all("th")
                ]
                rows = []
                for tr in table.find_all("tr"):
                    if not isinstance(tr, Tag):
                        continue
                    cols = [
                        td.get_text(strip=True) for td in tr.find_all("td")
                    ]
                    if cols and len(cols) == len(headers):
                        row_data = {}
                        for i, header in enumerate(headers):
                            row_data[header] = cols[i]
                        rows.append(row_data)

                for row in rows[:-1]:
                    cotizaciones_data.append(AFCCotizacionEntry(
                        period=row.get("Período", "").strip(),
                        employer_rut=row.get("RUT Empleador", ""),
                        employer_name=row.get("Razón Social", ""),
                        taxable_income=parse_money(
                            row.get("Renta Imponible", "0")),
                        contributed_amount=parse_money(
                            row.get("Monto Cotizado", "0")),
                        payment_date=row.get("Fecha de Pago", "")
                    ))
            else:
                logger.warning(
                    f"Cotizaciones table for year {year} not found or is not a valid HTML table element. "
                )
        else:
            logger.warning(
                f"Cotizaciones table element for year {year} not found by Playwright."
            )
        return cotizaciones_data
