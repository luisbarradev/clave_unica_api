
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from typing import Dict, List, TypedDict


class AFCEmpresaEntry(TypedDict):
    """Represents a single company entry from the AFC scraper."""

    employer_rut: str
    employer_name: str
    start_date: str
    end_date: str
    status: str

class AFCCotizacionEntry(TypedDict):
    """Represents a single contribution entry from the AFC scraper."""

    period: str
    employer_rut: str
    employer_name: str
    taxable_income: int
    contributed_amount: int
    payment_date: str

class AFCScraperResult(TypedDict):
    """Represents the complete result of the AFC scraper."""

    companies_data: List[AFCEmpresaEntry]
    contributions_data: Dict[str, List[AFCCotizacionEntry]]
    timestamp: str
    currency: str
