from typing import List, TypedDict
from datetime import datetime


class DebtEntry(TypedDict):
    institution: str
    credit_type: str
    total_credit: int
    current: int
    late_30_59: int
    late_60_89: int
    late_90_plus: int


class DebtTotals(TypedDict):
    total_credit: int
    current: int
    late_30_59: int
    late_60_89: int
    late_90_plus: int


class CMFScraperResult(TypedDict):
    data: List[DebtEntry]
    totals: DebtTotals
    timestamp: str
    currency: str


class LineOfCreditEntry(TypedDict):
    institution: str
    direct: int
    indirect: int


class LineOfCreditTotals(TypedDict):
    direct: int
    indirect: int


class CMFLineOfCreditResult(TypedDict):
    data: List[LineOfCreditEntry]
    totals: LineOfCreditTotals
    timestamp: str
    currency: str


class HasCreditLinesResult(TypedDict):
    direct: bool
    indirect: bool
