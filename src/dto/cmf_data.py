from typing import List, TypedDict


class DebtEntry(TypedDict):
    """Represents a single debt entry from the CMF scraper."""

    institution: str
    credit_type: str
    total_credit: int
    current: int
    late_30_59: int
    late_60_89: int
    late_90_plus: int


class DebtTotals(TypedDict):
    """Represents the total debt amounts from the CMF scraper."""

    total_credit: int
    current: int
    late_30_59: int
    late_60_89: int
    late_90_plus: int


class CMFScraperResult(TypedDict):
    """Represents the complete debt data result from the CMF scraper."""

    data: List[DebtEntry]
    totals: DebtTotals
    timestamp: str
    currency: str


class LineOfCreditEntry(TypedDict):
    """Represents a single line of credit entry from the CMF scraper."""

    institution: str
    direct: int
    indirect: int


class LineOfCreditTotals(TypedDict):
    """Represents the total line of credit amounts from the CMF scraper."""

    direct: int
    indirect: int


class CMFLineOfCreditResult(TypedDict):
    """Represents the complete line of credit data result from the CMF scraper."""

    data: List[LineOfCreditEntry]
    totals: LineOfCreditTotals
    timestamp: str
    currency: str


class HasCreditLinesResult(TypedDict):
    """Represents the result of checking for available credit lines."""

    direct: bool
    indirect: bool
