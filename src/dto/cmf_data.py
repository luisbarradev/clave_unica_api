from typing import List, TypedDict

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