from src.config.config import NETWORK_IDLE_TIMEOUT
from src.scrapers.base_scraper import BaseScraper
from src.scrapers.captcha_solver import RecaptchaSolver

__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import datetime
from typing import Dict, List, Any

from bs4 import BeautifulSoup, Tag
from playwright.async_api import BrowserContext, Page, Frame

from src.config.logger import get_logger, log_execution_func
from src.dto.sii_data import (
    SiiAcreditarRentaResult,
    SiiHeaderData,
    SiiContributorData,
    SiiPropertyData,
    SiiHonoraryTicketData,
    SiiTaxDeclarationData,
    SiiEconomicActivity,
    SiiLastStampedDocument,
    SiiPropertyEntry,
    SiiHonoraryTicketEntry,
    SiiTaxDeclarationEntry
)
from src.models.clave_unica import ClaveUnica
from src.scrapers.login_scraper import LoginScraper
from src.utils.utils import parse_money

logger = get_logger(__name__)


class SIIScraper(BaseScraper):
    """Scraper for SII (Servicio de Impuestos Internos) data, specifically for 'Acreditar Renta'."""

    def __init__(self, context: BrowserContext, login_scraper: LoginScraper, clave_unica: ClaveUnica,
                 captcha_solver: RecaptchaSolver):
        self.context = context
        self.login_scraper = login_scraper
        self.clave_unica = clave_unica
        self.captcha_solver = captcha_solver

    @log_execution_func
    async def run(self) -> SiiAcreditarRentaResult:
        """Runs the SII scraper to extract 'Acreditar Renta' data."""
        page = await self.context.new_page()

        login_url = "https://zeusr.sii.cl/cgi_AUT2000/InitClaveUnicaP.cgi?code=411&REF=https://misiir.sii.cl/cgi_misii/siihome.cgi-GATO-"
        await page.goto(login_url)
        await self.login_scraper.do_login(page, self.clave_unica)

        carpeta_tributaria_page = "https://zeus.sii.cl/dii_cgi/carpeta_tributaria/cte_acreditar_renta_00.cgi"
        await page.goto(carpeta_tributaria_page)

        # Switch to the frame
        frame = page.frame(name="cte")
        if not frame:
            raise Exception("Could not find the frame with name 'cte'")

        # Extract data from the page
        header_data = await self._scrape_header_data(frame)
        contributor_data = await self._scrape_contributor_data(frame)
        property_data = await self._scrape_property_data(frame)
        honorary_ticket_data = await self._scrape_honorary_ticket_data(frame)
        tax_declaration_data = await self._scrape_tax_declaration_data(frame)

        return SiiAcreditarRentaResult(
            header_data=header_data,
            contributor_data=contributor_data,
            property_data=property_data,
            honorary_ticket_data=honorary_ticket_data,
            tax_declaration_data=tax_declaration_data,
            timestamp=datetime.datetime.now().isoformat(),
            currency="CLP"
        )

    @log_execution_func
    async def _scrape_header_data(self, page: Page | Frame) -> SiiHeaderData:
        """Extracts header data from hidden input fields."""
        rut = await page.locator("input#rut").get_attribute("value") or ""
        dv = await page.locator("input#dv").get_attribute("value") or ""
        fecha_emision = await page.locator("input#fecha_emision").get_attribute("value") or ""
        nombre_completo = await page.locator("input#nombre_completo").get_attribute("value") or ""
        mail = await page.locator("input#mail").get_attribute("value") or ""
        codigo = await page.locator("input#codigo").get_attribute("value") or ""

        return SiiHeaderData(
            rut=rut,
            dv=dv,
            generation_date=fecha_emision,
            full_name=nombre_completo,
            email=mail,
            code=codigo
        )

    async def _scrape_contributor_data(self, page: Page | Frame) -> SiiContributorData:
        """Extracts contributor data from the hidden input field tbl_dbcontribuyente1."""
        html_content = await page.locator('input[name="tbl_dbcontribuyente1"]').get_attribute("value") or ""
        soup = BeautifulSoup(html_content, "html.parser")

        start_date_activities_tag = soup.find(id="td_fecha_inicio")
        start_date_activities = start_date_activities_tag.get_text(
            strip=True) if start_date_activities_tag else ""

        economic_activities_raw_tag = soup.find(id="td_actividades")
        economic_activities_text = economic_activities_raw_tag.get_text(
            separator="\n", strip=True).replace(u'\xa0', ' ') if isinstance(economic_activities_raw_tag, Tag) else ""
        economic_activities: List[SiiEconomicActivity] = []
        for line in economic_activities_text.splitlines():
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                if len(parts) > 1 and parts[0].isdigit():
                    economic_activities.append(SiiEconomicActivity(
                        code=parts[0], description=parts[1].strip()))
                else:
                    economic_activities.append(
                        SiiEconomicActivity(code="", description=line))

        tax_category_tag = soup.find(id="td_categoria")
        tax_category = tax_category_tag.get_text(
            strip=True) if tax_category_tag else ""
        address_tag = soup.find(id="td_domicilio")
        address = address_tag.get_text(strip=True) if address_tag else ""
        branches_tag = soup.find("td", string="Sucursales:")
        branches = ""
        if branches_tag:
            next_sibling = branches_tag.find_next_sibling("td")
            if next_sibling:
                branches = next_sibling.get_text(strip=True)

        last_stamped_documents: List[SiiLastStampedDocument] = []
        doc_names_tag = soup.find(id="td_tim_nombre")
        doc_names = doc_names_tag.get_text(
            separator="\n", strip=True) if isinstance(doc_names_tag, Tag) else ""
        doc_dates_tag = soup.find(id="td_tim_fecha")
        doc_dates = doc_dates_tag.get_text(
            separator="\n", strip=True) if isinstance(doc_dates_tag, Tag) else ""

        for name, date in zip(doc_names.splitlines(), doc_dates.splitlines()):
            name = name.strip()
            date = date.strip()
            if name:
                last_stamped_documents.append(
                    SiiLastStampedDocument(document_type=name, date=date))

        tax_observations_tag = soup.find(id="td_observaciones")
        tax_observations = tax_observations_tag.get_text(
            strip=True) if tax_observations_tag else ""

        return SiiContributorData(
            start_date_activities=start_date_activities,
            economic_activities=economic_activities,
            tax_category=tax_category,
            address=address,
            branches=branches if branches else None,
            last_stamped_documents=last_stamped_documents,
            tax_observations=tax_observations
        )

    @log_execution_func
    async def _scrape_property_data(self, page: Page | Frame) -> SiiPropertyData:
        """Extracts property data from the hidden input field tbl_propiedades1."""
        html_content = await page.locator("input[name=\"tbl_propiedades1\"]").get_attribute("value") or ""
        soup = BeautifulSoup(html_content, "html.parser")

        properties: List[SiiPropertyEntry] = []
        # Find the table body that contains the property data, excluding the header and footer rows
        table = soup.find("table")
        if table and isinstance(table, Tag):
            rows = table.find_all("tr")
            # Skip header row and notes/summary rows
            data_rows = [row for row in rows if isinstance(row, Tag) and (center_td := row.find("td", class_="centeralign")) and isinstance(
                center_td, Tag) and "- No se registra información para este RUT -" not in center_td.get_text(strip=True)]

            if not data_rows and "- No se registra información para este RUT -" in table.get_text():
                # No properties found
                pass
            else:
                # Assuming the first tr is header, and the last tr is notes
                # Adjust slicing based on actual HTML structure if needed
                for row in rows[2:-1]:  # Skip header and notes rows
                    if isinstance(row, Tag):
                        cols = row.find_all("td")
                        if len(cols) == 8:  # Ensure it's a data row
                            try:
                                properties.append(SiiPropertyEntry(
                                    commune=cols[0].get_text(strip=True),
                                    role=cols[1].get_text(strip=True),
                                    address=cols[2].get_text(strip=True),
                                    destination=cols[3].get_text(strip=True),
                                    fiscal_appraisal=parse_money(
                                        cols[4].get_text(strip=True)),
                                    outstanding_installments_due=parse_money(
                                        cols[5].get_text(strip=True)),
                                    outstanding_installments_current=parse_money(
                                        cols[6].get_text(strip=True)),
                                    condition=cols[7].get_text(strip=True)
                                ))
                            except ValueError as e:
                                logger.warning(
                                    f"Error parsing property data: {e} in row {row.get_text()}")

        notes: List[str] = []
        notes_p = soup.find("td", class_="td_tbl_background").find(  # type: ignore
            "p") if soup.find("td", class_="td_tbl_background") else None
        if notes_p:
            for content in notes_p.contents:  # type: ignore
                if isinstance(content, str) and content.strip():
                    notes.append(content.strip())
                elif content.name == 'br':  # type: ignore
                    pass  # Ignore <br> tags for now, or handle as new line if needed

        return SiiPropertyData(
            properties=properties,
            notes=notes
        )

    async def _scrape_honorary_ticket_data(self, page: Page | Frame) -> SiiHonoraryTicketData:
        """Extracts honorary ticket data from the hidden input field tbl_boletas1."""
        html_content = await page.locator('input[name="tbl_boletas1"]').get_attribute("value") or ""
        soup = BeautifulSoup(html_content, "html.parser")

        tickets: List[SiiHonoraryTicketEntry] = []
        table = soup.find("table")
        if table and isinstance(table, Tag):
            all_rows = table.find_all("tr")
            rows = [row for row in all_rows if isinstance(row, Tag)]
            for row in rows[2:-1]:  # Skip header and notes rows
                if isinstance(row, Tag):
                    cols = row.find_all("td")
                    # Ensure it's a data row and not the totals row
                    if len(cols) == 4 and "Totales:" not in row.get_text(strip=True):
                        try:
                            tickets.append(SiiHonoraryTicketEntry(
                                period=cols[0].get_text(strip=True),
                                gross_honorary=parse_money(
                                    cols[1].get_text(strip=True) or "0"),
                                third_party_retention=parse_money(
                                    cols[2].get_text(strip=True) or "0"),
                                contributor_ppm=parse_money(
                                    cols[3].get_text(strip=True) or "0")
                            ))
                        except ValueError as e:
                            logger.warning(
                                f"Error parsing honorary ticket data: {e} in row {row.get_text()}")

        note = ""
        note_p = soup.find("td", colspan="4", class_="td_tbl_background").find(  # type: ignore
            "p") if soup.find("td", colspan="4", class_="td_tbl_background") else None
        if note_p:
            note = note_p.get_text(strip=True)  # type: ignore

        return SiiHonoraryTicketData(
            tickets=tickets,
            note=note
        )

    @log_execution_func
    async def _scrape_tax_declaration_data(self, page: Page | Frame) -> SiiTaxDeclarationData:
        """Extracts tax declaration data (F22) directly from the page."""
        declarations: List[SiiTaxDeclarationEntry] = []

        # Find all sections for tax declarations (e.g., Año Tributario 2025, Año Tributario 2024)
        declaration_sections = await page.locator("div#marca_RENTA table#tbl_renta > tbody > tr:has(td.td_tbl_background span.textof)").all()

        for i, section_locator in enumerate(declaration_sections):
            tax_year_text = await section_locator.locator("td.td_tbl_background span.textof").first.inner_text()
            try:
                tax_year = int(tax_year_text.split()[-1])
            except (ValueError, IndexError):
                logger.warning(
                    f"Could not parse tax year from: {tax_year_text}")
                continue

            # The form number is usually next to the tax year, e.g., "1 / 3"
            form_number_text = await section_locator.locator("td.td_tbl_background span.textof").nth(1).inner_text()
            form_number = form_number_text.strip()

            details: Dict[str, Any] = {}
            # Locate the div containing the form details, which is usually the next sibling tr's div
            # This might need adjustment based on the exact HTML structure if it varies
            # Assuming IDs are n_renta_1, n_renta_2, etc.
            details_div_locator = page.locator(f"#n_renta_{i+1}")

            if await details_div_locator.count() > 0:
                details_html = await details_div_locator.inner_html()
                details_soup = BeautifulSoup(details_html, "html.parser")

                # Check for "- No se registra declaración para este período -"
                if "- No se registra declaración para este período -" in details_soup.get_text():
                    # No declaration for this period
                    pass
                else:
                    # Extract data from the table within the details div
                    # This part is complex due to the dynamic nature of the F22 form
                    # We need to find rows with code and concept, and then the value
                    # Iterate through all rows in the details section
                    for row in details_soup.find_all("tr"):
                        if isinstance(row, Tag):
                            cells = row.find_all("td")
                            if len(cells) >= 6:
                                code1_tag = cells[0].find("b")  # type: ignore
                                concept1_tag = cells[1].find(  # type: ignore
                                    "font")  # type: ignore
                                value1_tag = cells[2]

                                if code1_tag and isinstance(code1_tag, Tag) and \
                                   concept1_tag and isinstance(concept1_tag, Tag) and \
                                   value1_tag and isinstance(value1_tag, Tag):
                                    code1 = ' '.join(
                                        code1_tag.get_text(strip=True).split())
                                    concept1 = ' '.join(concept1_tag.get_text(
                                        separator=' ', strip=True).split())
                                    value1 = ' '.join(value1_tag.get_text(
                                        separator=' ', strip=True).split())
                                    if not code1.startswith('AÑO'):
                                        details[code1] = {
                                            "concept": concept1, "value": value1}

                                code2_tag = cells[3].find("b")  # type: ignore
                                concept2_tag = cells[4].find(  # type: ignore
                                    "font")  # type: ignore
                                value2_tag = cells[5]

                                if code2_tag and isinstance(code2_tag, Tag) and \
                                   concept2_tag and isinstance(concept2_tag, Tag) and \
                                   value2_tag and isinstance(value2_tag, Tag):
                                    code2 = ' '.join(
                                        code2_tag.get_text(strip=True).split())
                                    concept2 = ' '.join(concept2_tag.get_text(
                                        separator=' ', strip=True).split())
                                    value2 = ' '.join(value2_tag.get_text(
                                        separator=' ', strip=True).split())
                                    if not code2.startswith('AÑO'):
                                        details[code2] = {
                                            "concept": concept2, "value": value2}

            declarations.append(SiiTaxDeclarationEntry(
                tax_year=tax_year,
                form_number=form_number,
                details=details
            ))

        return SiiTaxDeclarationData(
            declarations=declarations
        )
