from datetime import date
from typing import Literal

from pydantic import BaseModel

InsuranceStatus = Literal["social", "employment", "none"]


class PayrollRow(BaseModel):
    employee_id: int
    employee_name: str
    total_hours: float
    overnight_hours: float
    base_wage: int
    overnight_premium: int
    transport_cost_total: int
    insurance_status: InsuranceStatus
    grand_total: int


class PayrollDay(BaseModel):
    target_date: date
    total_cost: int
    headcount: int


class PayrollReport(BaseModel):
    year: int
    month: int
    rows: list[PayrollRow]
    per_day: list[PayrollDay]
    monthly_total: int
