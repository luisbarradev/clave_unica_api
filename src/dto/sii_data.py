from typing import List, TypedDict, Dict, Any, Optional

class SiiHeaderData(TypedDict):
    rut: str
    dv: str
    generation_date: str
    full_name: str
    email: str
    code: str

class SiiEconomicActivity(TypedDict):
    code: str
    description: str

class SiiLastStampedDocument(TypedDict):
    document_type: str
    date: str

class SiiContributorData(TypedDict):
    start_date_activities: str
    economic_activities: List[SiiEconomicActivity]
    tax_category: str
    address: str
    branches: Optional[str]
    last_stamped_documents: List[SiiLastStampedDocument]
    tax_observations: str

class SiiPropertyEntry(TypedDict):
    commune: str
    role: str
    address: str
    destination: str
    fiscal_appraisal: int
    outstanding_installments_due: int
    outstanding_installments_current: int
    condition: str

class SiiPropertyData(TypedDict):
    properties: List[SiiPropertyEntry]
    notes: List[str]

class SiiHonoraryTicketEntry(TypedDict):
    period: str
    gross_honorary: int
    third_party_retention: int
    contributor_ppm: int

class SiiHonoraryTicketData(TypedDict):
    tickets: List[SiiHonoraryTicketEntry]
    note: str

class SiiTaxDeclarationEntry(TypedDict):
    tax_year: int
    form_number: str
    details: Dict[str, Any] # Key is the code (str), value is the data (Any)

class SiiTaxDeclarationData(TypedDict):
    declarations: List[SiiTaxDeclarationEntry]

class SiiAcreditarRentaResult(TypedDict):
    header_data: SiiHeaderData
    contributor_data: SiiContributorData
    property_data: SiiPropertyData
    honorary_ticket_data: SiiHonoraryTicketData
    tax_declaration_data: SiiTaxDeclarationData
    timestamp: str
    currency: str
