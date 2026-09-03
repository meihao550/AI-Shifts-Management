from datetime import date
from typing import Literal

from pydantic import BaseModel

InsuranceStatus = Literal["social", "employment", "none"]


class PayrollRow(BaseModel):
    employee_id: int
    employee_name: str
    total_hours: float  # 総スパン（休憩を引かない拘束時間）
    worked_hours: float  # 実働時間（総スパン − 休憩）。賃金・保険判定の基礎
    overnight_hours: float
    base_wage: int
    overnight_premium: int
    transport_cost_total: int
    paid_leave_days: int
    paid_leave_total: int
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
    warnings: list[str] = []
