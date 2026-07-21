"""Japanese holiday routes (read-only, backed by jpholiday)."""

import jpholiday
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/holidays", tags=["holidays"])


class Holiday(BaseModel):
    date: str  # ISO date (YYYY-MM-DD)
    name: str


@router.get("", response_model=list[Holiday])
def list_holidays(year: int, month: int | None = None) -> list[Holiday]:
    """Return Japanese public holidays for a year, optionally filtered by month."""
    pairs = (
        jpholiday.month_holidays(year, month)
        if month is not None
        else jpholiday.year_holidays(year)
    )
    return [Holiday(date=d.isoformat(), name=name) for d, name in pairs]
