
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from typing import TypedDict, List, Dict

class AFCEmpresaEntry(TypedDict):
    employer_rut: str
    employer_name: str
    start_date: str
    end_date: str
    status: str

class AFCCotizacionEntry(TypedDict):
    period: str
    employer_rut: str
    employer_name: str
    taxable_income: int
    contributed_amount: int
    payment_date: str

class AFCScraperResult(TypedDict):
    companies_data: List[AFCEmpresaEntry]
    contributions_data: Dict[str, List[AFCCotizacionEntry]]
    timestamp: str
    currency: str
